import numpy as np
import matplotlib.pyplot as plt


class IconSet:
  def __init__(self, raw_color_palette_data):
    self._color_map_rgb = self._init_color_map_rgb(raw_color_palette_data)
    self._icons = []

  def _init_color_map_rgb(self, raw_color_palette_data):
    # Hexa value (shift) indexed to the color palette (0 to F): Left nibble is the 2nd pixel.
    # ex: [0x4f, 0x9e] -> [f, 4, e, 9]
    color_map = np.array(
      list(raw_color_palette_data)
    ).reshape((16, 2))
    # color map little endian
    # ex: [0xff, 0x7f] -> 0x7fff
    color_map_16b = [
      color[1]//16*16**3+color[1]%16*16**2+color[0]
      for color in color_map
    ]
    return [self._transform_to_rgb(color) for color in color_map_16b]

  def _transform_to_rgb(self, color):
    # 0-4   Red       (0..31)         ;\Color 0000h        = Fully-Transparent
    # 5-9   Green     (0..31)         ; Color 0001h..7FFFh = Non-Transparent
    # 10-14 Blue      (0..31)         ; Color 8000h..FFFFh = Semi-Transparent (*)
    # 15    Semi Transparency Flag    ;/(*) or Non-Transparent for opaque commands
    rgb = []
    for _ in range(0,3):
      rgb.append(color & (0b11111))
      color = color >> 5
    return np.array(rgb)/31

  def generate_icon_from_data(self, raw_icon_data):
    self._icons.append(
      Icon(
        len(self._icons)+1,
        self._color_map_rgb, 
        raw_icon_data
      )
    )


class Icon:
  def __init__(self, icon_number, color_map_rgb, raw_icon_data):
    self._icon_number = icon_number
    self._raw_icon_data = raw_icon_data
    self._color_map_rgb = color_map_rgb
    self._transform_icon_data()

  def _transform_icon_data(self):
    icon_data = np.concatenate([
      [pixel%16, pixel//16] for pixel in list(self._raw_icon_data)
    ])
    self._icon_data_rgb = np.array(
      [self._color_map_rgb[pixel_value] for pixel_value in icon_data]
    ).reshape((16, 16, 3))

  def plot_icon(self, save=False):
    plt.axis('off')
    plt.imshow(self._icon_data_rgb)
    if save:
      plt.savefig(f'icon_{self._icon_number}.png', bbox_inches='tight')
    plt.show()
