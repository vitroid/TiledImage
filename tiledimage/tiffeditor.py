import logging
import os
from typing import Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
import tifffile
import rasterio
from rasterio.windows import Window
from rasterio import Affine


@dataclass
class Range:
    """数値の範囲を表現するクラス"""

    min_val: int
    max_val: int

    @property
    def width(self) -> int:
        """範囲の幅を返す"""
        return self.max_val - self.min_val


@dataclass
class Rect:
    """2次元の領域を表現するクラス"""

    x_range: Range
    y_range: Range

    @classmethod
    def from_coords(cls, x_min: int, x_max: int, y_min: int, y_max: int) -> "Rect":
        """座標からRectを作成する"""
        return cls(Range(x_min, x_max), Range(y_min, y_max))


class TiffEditor:
    """
    TIFFファイルの部分編集を可能にするクラス

    メモリ効率の良い方法で巨大なTIFFファイルの部分的な読み書きを行う。
    TiledImageの設計思想を参考に、ディスク上のTIFFファイルを直接操作する。

    Features:
    - 部分的な読み込み（メモリ効率）
    - 部分的な書き込み（既存ファイルの更新）
    - タイル構造の活用
    - スライス記法での操作
    """

    def __init__(
        self,
        filepath: str,
        mode: str = "r+",
        tilesize: Union[int, Tuple[int, int]] = 512,
        dtype: Optional[np.dtype] = None,
        shape: Optional[Tuple[int, int, int]] = None,
        create_if_not_exists: bool = False,
    ):
        """
        TiffEditorを初期化する

        Args:
            filepath: TIFFファイルのパス
            mode: ファイルのオープンモード ('r', 'r+', 'w')
            tilesize: タイルサイズ（int または (width, height)のタプル）
            dtype: データ型（新規作成時）
            shape: 画像の形状 (height, width, channels)（新規作成時）
            create_if_not_exists: ファイルが存在しない場合に新規作成するか
        """
        self.filepath = filepath
        self.mode = mode

        if isinstance(tilesize, int):
            self.tilesize = (tilesize, tilesize)
        else:
            self.tilesize = tilesize

        self._tiff_handle = None
        self._rasterio_handle = None
        self.logger = logging.getLogger(__name__)

        # ファイルが存在しない場合の処理
        if not os.path.exists(filepath):
            if create_if_not_exists and mode in ["w", "r+"]:
                if shape is None or dtype is None:
                    raise ValueError("新規作成時はshapeとdtypeを指定してください")
                self._create_tiff_file(shape, dtype)
                # ファイル作成後に再度オープンを試行
                self._open_file()
            elif mode != "w":
                raise FileNotFoundError(f"ファイルが見つかりません: {filepath}")
        else:
            self._open_file()

    def _create_tiff_file(self, shape: Tuple[int, int, int], dtype: np.dtype):
        """新しいタイル化TIFFファイルを作成する"""
        height, width, channels = shape

        # ダミーデータで初期化
        dummy_data = np.zeros((height, width, channels), dtype=dtype)

        # タイル化TIFFとして保存
        tifffile.imwrite(
            self.filepath,
            dummy_data,
            tile=self.tilesize,
            photometric="rgb" if channels == 3 else "minisblack",
        )

        self.logger.info(f"新しいTIFFファイルを作成しました: {self.filepath}")

    def _open_file(self):
        """ファイルを開く"""
        try:
            if self.mode == "r":
                # 読み込み専用の場合はtifffileを使用
                self._tiff_handle = tifffile.TiffFile(self.filepath)
            else:
                # 読み書きの場合はrasterioを使用
                # ファイルが存在するかチェック
                if os.path.exists(self.filepath):
                    self._rasterio_handle = rasterio.open(self.filepath, "r+")
                else:
                    # ファイルが存在しない場合は何もしない（_create_tiff_fileの後で再度呼ばれる）
                    pass

        except Exception as e:
            raise IOError(f"ファイルを開けませんでした: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """ファイルハンドルを閉じる"""
        if self._tiff_handle:
            self._tiff_handle.close()
            self._tiff_handle = None
        if self._rasterio_handle:
            self._rasterio_handle.close()
            self._rasterio_handle = None

    @property
    def shape(self) -> Tuple[int, int, int]:
        """画像の形状を取得"""
        if self._rasterio_handle:
            height, width = self._rasterio_handle.height, self._rasterio_handle.width
            channels = self._rasterio_handle.count
        elif self._tiff_handle:
            page = self._tiff_handle.pages[0]
            height, width = page.shape[:2]
            channels = page.shape[2] if len(page.shape) > 2 else 1
        else:
            raise ValueError("ファイルが開かれていません")

        return (height, width, channels)

    @property
    def dtype(self) -> np.dtype:
        """データ型を取得"""
        if self._rasterio_handle:
            return self._rasterio_handle.dtypes[0]
        elif self._tiff_handle:
            return self._tiff_handle.pages[0].dtype
        else:
            raise ValueError("ファイルが開かれていません")

    def _parse_slice(self, key) -> Rect:
        """スライスを解析してRectに変換する（TiledImageと同じ）"""
        if not isinstance(key, tuple) or len(key) != 2:
            raise IndexError("2次元のスライスを指定してください")

        y_slice, x_slice = key
        if not (isinstance(y_slice, slice) and isinstance(x_slice, slice)):
            raise IndexError("スライスを指定してください")

        # 画像の実際のサイズを取得
        height, width, _ = self.shape

        # スライスの開始と終了を取得
        y_start = y_slice.start if y_slice.start is not None else 0
        y_stop = y_slice.stop if y_slice.stop is not None else height
        x_start = x_slice.start if x_slice.start is not None else 0
        x_stop = x_slice.stop if x_slice.stop is not None else width

        # 範囲チェック
        y_start = max(0, min(y_start, height))
        y_stop = max(0, min(y_stop, height))
        x_start = max(0, min(x_start, width))
        x_stop = max(0, min(x_stop, width))

        # ステップは未対応
        if y_slice.step is not None or x_slice.step is not None:
            raise NotImplementedError("ステップ付きスライスには未対応です")

        return Rect.from_coords(x_start, x_stop, y_start, y_stop)

    def __getitem__(self, key) -> np.ndarray:
        """スライスで領域を取得する"""
        region = self._parse_slice(key)
        return self.get_region(region)

    def __setitem__(self, key, value: np.ndarray):
        """スライスで領域を設定する"""
        if not isinstance(value, np.ndarray):
            raise TypeError("NumPy配列を指定してください")

        region = self._parse_slice(key)
        self.put_region(region, value)

    def get_region(self, region: Rect) -> np.ndarray:
        """指定された領域のデータを読み込む"""
        x_start = region.x_range.min_val
        x_stop = region.x_range.max_val
        y_start = region.y_range.min_val
        y_stop = region.y_range.max_val

        width = x_stop - x_start
        height = y_stop - y_start

        if width <= 0 or height <= 0:
            return np.array([])

        if self._rasterio_handle:
            # rasterioを使用した読み込み
            window = Window(x_start, y_start, width, height)
            data = self._rasterio_handle.read(window=window)

            # rasterioは(channels, height, width)で返すので転置
            if data.ndim == 3:
                data = np.transpose(data, (1, 2, 0))
            else:
                data = data[0]  # 単一チャンネルの場合

        elif self._tiff_handle:
            # tifffileを使用した読み込み
            page = self._tiff_handle.pages[0]
            data = page.asarray()[y_start:y_stop, x_start:x_stop]

        else:
            raise ValueError("ファイルが開かれていません")

        self.logger.debug(f"領域を読み込みました: {region}, shape: {data.shape}")
        return data

    def put_region(self, region: Rect, data: np.ndarray):
        """指定された領域にデータを書き込む"""
        if self.mode == "r":
            raise ValueError("読み込み専用モードでは書き込みできません")

        x_start = region.x_range.min_val
        x_stop = region.x_range.max_val
        y_start = region.y_range.min_val
        y_stop = region.y_range.max_val

        width = x_stop - x_start
        height = y_stop - y_start

        if width <= 0 or height <= 0:
            return

        # データサイズの検証
        expected_shape = (height, width)
        if data.ndim == 3:
            expected_shape = (height, width, data.shape[2])
        elif data.ndim == 2:
            expected_shape = (height, width)
        else:
            raise ValueError(f"不正なデータ形状: {data.shape}")

        if data.shape[:2] != (height, width):
            raise ValueError(
                f"データサイズが一致しません。期待: {expected_shape}, 実際: {data.shape}"
            )

        if self._rasterio_handle:
            # rasterioを使用した書き込み
            window = Window(x_start, y_start, width, height)

            if data.ndim == 3:
                # (height, width, channels) -> (channels, height, width)
                write_data = np.transpose(data, (2, 0, 1))
                for i in range(write_data.shape[0]):
                    self._rasterio_handle.write(write_data[i], i + 1, window=window)
            else:
                # 単一チャンネル
                self._rasterio_handle.write(data, 1, window=window)

        else:
            raise ValueError("書き込みにはrasterioハンドルが必要です")

        self.logger.debug(f"領域に書き込みました: {region}, shape: {data.shape}")

    def get_info(self) -> dict:
        """ファイルの情報を取得する"""
        shape = self.shape
        dtype = self.dtype

        info = {
            "filepath": self.filepath,
            "shape": shape,
            "dtype": str(dtype),
            "size_mb": os.path.getsize(self.filepath) / (1024 * 1024),
            "tilesize": self.tilesize,
        }

        if self._rasterio_handle:
            info.update(
                {
                    "compression": getattr(
                        self._rasterio_handle, "compression", "unknown"
                    ),
                    "photometric": getattr(
                        self._rasterio_handle, "photometric", "unknown"
                    ),
                    "is_tiled": getattr(self._rasterio_handle, "is_tiled", False),
                }
            )

        return info


def create_sample_tiff(filepath: str, shape: Tuple[int, int, int], tilesize: int = 512):
    """サンプルのタイル化TIFFファイルを作成する関数"""
    height, width, channels = shape

    # グラデーションパターンを作成
    y_coords, x_coords = np.mgrid[0:height, 0:width]

    if channels == 3:
        # カラーグラデーション
        r = (x_coords / width * 255).astype(np.uint8)
        g = (y_coords / height * 255).astype(np.uint8)
        b = ((x_coords + y_coords) / (width + height) * 255).astype(np.uint8)
        data = np.stack([r, g, b], axis=2)
    else:
        # グレースケールグラデーション
        data = ((x_coords + y_coords) / (width + height) * 255).astype(np.uint8)

    # タイル化TIFFとして保存
    tifffile.imwrite(
        filepath,
        data,
        tile=(tilesize, tilesize),
        photometric="rgb" if channels == 3 else "minisblack",
    )

    return filepath


def test_tiff_editor():
    """TiffEditorのテスト関数"""
    import tempfile
    import cv2

    logging.basicConfig(level=logging.DEBUG)

    # テスト用の一時ファイル
    with tempfile.NamedTemporaryFile(suffix=".tiff", delete=False) as tmp:
        temp_filepath = tmp.name

    try:
        # サンプルTIFFファイルを作成
        print("サンプルTIFFファイルを作成中...")
        create_sample_tiff(temp_filepath, (2000, 3000, 3), tilesize=256)

        # TiffEditorでファイルを開く
        with TiffEditor(temp_filepath, mode="r+") as editor:
            print(f"ファイル情報: {editor.get_info()}")

            # 部分的に読み込み
            print("部分読み込みテスト...")
            region_data = editor[100:300, 200:400]  # 200x200の領域
            print(f"読み込んだ領域の形状: {region_data.shape}")

            # 読み込んだ領域を変更
            print("部分書き込みテスト...")
            modified_data = np.zeros_like(region_data)
            modified_data[:, :, 0] = 255  # 赤色にする
            editor[100:300, 200:400] = modified_data

            # 変更を確認
            print("変更確認...")
            verification_data = editor[100:300, 200:400]
            print(f"変更後の平均値 (R,G,B): {np.mean(verification_data, axis=(0,1))}")

            # 別の領域を読み込んで表示用に保存
            display_region = editor[0:500, 0:500]
            cv2.imwrite(
                "tiff_editor_test_output.png",
                cv2.cvtColor(display_region, cv2.COLOR_RGB2BGR),
            )
            print("テスト結果を 'tiff_editor_test_output.png' に保存しました")

        print("TiffEditorのテストが完了しました！")

    finally:
        # 一時ファイルを削除
        if os.path.exists(temp_filepath):
            os.unlink(temp_filepath)


def test():
    import sys
    import cv2
    import logging

    logging.basicConfig(level=logging.DEBUG)

    png = sys.argv[1]
    tilesize = int(sys.argv[2])

    # 元画像を読み込んでサイズを取得
    original_image = cv2.imread(png)
    if original_image is None:
        print(f"エラー: 画像ファイル '{png}' が見つかりません")
        return

    height, width, channels = original_image.shape
    print(f"元画像サイズ: {height}x{width}x{channels}")

    # TIFFファイルを新規作成（十分な大きさで）
    tiff_height = height + 100  # 余裕を持たせる
    tiff_width = width + 100

    with TiffEditor(
        filepath=png + ".tiff",
        mode="r+",
        tilesize=tilesize,
        shape=(tiff_height, tiff_width, channels),
        dtype=np.uint8,
        create_if_not_exists=True,
    ) as tiff_editor:
        print(f"TIFFファイル情報: {tiff_editor.get_info()}")

        # BGRからRGBに変換
        rgb_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

        # 画像を配置
        tiff_editor[20 : 20 + height, 40 : 40 + width] = rgb_image
        tiff_editor[10 : 10 + height, 20 : 20 + width] = rgb_image

        # 結果を取得して表示
        result_image = tiff_editor[0:tiff_height, 0:tiff_width]

        # RGBからBGRに戻して表示
        display_image = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)
        cv2.imshow("TIFF Editor Result", display_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        print(f"TIFFファイル '{png}.tiff' が作成されました")


if __name__ == "__main__":
    # test_tiff_editor()
    test()
