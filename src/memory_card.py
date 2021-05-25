import codecs
from functools import reduce
import numpy as np
import struct

from icon import IconSet

KB = 1024
BLOCK_SIZE = 8*KB
FRAME_SIZE = BLOCK_SIZE//64
MAX_BLOCKS = 15


class MemoryCard:
  def __init__(self, path):
    self._path = path
    self._file_contents = None
    self._load_file_contents()
    self._directory_block = None
    self._generate_directory_block()
    self._blocks = {}
    self._generate_blocks()

  def _load_file_contents(self):
    expected_file_bytes_size = 128*KB
    with open(self._path, 'rb') as f:
      file_contents = f.read()
    if self._path.endswith(".gme"):
      file_contents = file_contents[0xF40:]
    if len(file_contents) != expected_file_bytes_size:
      raise Exception(
        f"Incompatible size: expecting {expected_file_bytes_size} bytes, got {len(file_contents)} bytes instead"
      )
    self._file_contents = file_contents

  def _block_raw_data_fetcher(self, block_count, starting_block):
    return self._file_contents[
      starting_block*BLOCK_SIZE:(starting_block+block_count)*BLOCK_SIZE
    ]

  def _generate_blocks(self):
    block_counter = 1
    game_ids_list = self._directory_block.get_game_ids_list()
    for game_id in game_ids_list:
      block_info = self._directory_block.get_info_for_game_id(game_id)
      block_count = block_info['block_count']
      block_raw_data = self._block_raw_data_fetcher(block_count, block_counter)
      self._blocks[game_id] = FileBlock(block_raw_data, block_count)
      block_counter += block_count
    if self._directory_block.free_blocks_left():
      self._blocks["BLANK"] = FileBlock.blank_block()

  def plot_icons_for_block(self, block_number, save=False):
    game_id = self._directory_block.get_game_id_for_block_location_number(block_number)
    for icon in self._blocks[game_id]._icon_set._icons:
      icon.plot_icon(save)

  def get_block_title(self, block_number):
    game_id = self._directory_block.get_game_id_for_block_location_number(block_number)
    try:
      title = self._blocks[game_id]._frames[0]._frame_data[0x04:(0x04+64)].decode('shift-jis')
    except UnicodeDecodeError:
      title = self._blocks[game_id]._frames[0]._frame_data[0x04:(0x04+32)].decode('shift-jis')
    return title

  def _generate_directory_block(self):
    self._directory_block = DirectoryBlock(self._file_contents[:BLOCK_SIZE])

  def delete_block_number(self, block_number):
    # CLEAN DIRECTORY BLOCK
    ### ON DIRECTORY BLOCK
    ### REMOVE DIRECTORY FRAME
    ### ADD BLANK FRAME ON THE LAST POSITION
    ### FIX DIRECTORY STRUCTURE

    # CLEAN BLOCKS DATA
    game_id = self._directory_block.get_game_id_for_block_location_number(block_number)
    self._blocks.pop(game_id)

  def make_binary(self):
    pass


class DirectoryBlock:

  def __init__(self, raw_data):
    self._block_raw_data = raw_data
    self._header_frame = None
    self._generate_header_frame()
    self._directory_frames = None
    self._generate_directory_frames()
    self._directory_structure = None
    self._generate_directory_structure()

  def _generate_header_frame(self):
    self._header_frame = DirectoryHeaderFrame(self._block_raw_data[:FRAME_SIZE])

  def _generate_directory_frames(self):
    self._directory_frames = [
      DirectoryFrame(self._block_raw_data[
        FRAME_SIZE*(frame_number):FRAME_SIZE*(frame_number+1)
      ]) for frame_number in range(1, 16)
    ]

  def _generate_directory_structure(self):
    parsed_directory_structure = [
      frame._parse_directory_frame() for frame in self._directory_frames
    ]
    self._directory_structure = self._fill_game_ids_for_multi_block(parsed_directory_structure)

  def _fill_game_ids_for_multi_block(self, parsed_directory_structure):
    filled_directory_structure = []
    previous_block_id = None
    for block_number, block_info in enumerate(parsed_directory_structure):
      block_in_use = block_info['block_state'] in BlockAllocationConstants.IN_USE
      if not block_info['game_id'] and block_in_use:
        block_info['game_id'] = previous_block_id
      elif not block_info['game_id']:
        block_info['game_id'] = "BLANK"
      filled_directory_structure.append(block_info)
      previous_block_id = block_info['game_id']
    return filled_directory_structure

  def get_info_for_game_id(self, game_id):
    for block_info in self._directory_structure:
      if game_id == block_info['game_id']:
        return block_info
    raise Exception(f"Not info in directory structure for game {game_id}.")

  def get_game_id_for_block_location_number(self, block_location_number):
    return self._directory_structure[block_location_number-1]['game_id']

  def get_game_ids_list(self):
    return [
      block_info['game_id'] for block_info 
      in self._directory_structure 
      if block_info['block_count'] > 0
    ]

  def free_blocks_left(self):
    return sum(
      [block_info['block_count'] for block_info in self._directory_structure]
    ) < MAX_BLOCKS

  def make_binary(self):
    binary_data = self._header_frame.make_binary()
    binary_data += b''.join([frame.make_binary() for frame in self._directory_frames])
    return binary_data


class BlockAllocationConstants:
  FIRST_BLOCK = 0x51
  MIDDLE_BLOCK = 0x52
  LAST_BLOCK = 0x53
  IN_USE = {FIRST_BLOCK, MIDDLE_BLOCK, LAST_BLOCK}


class FileBlock:
  def __init__(self, block_data, block_count):
    self._block_data = block_data
    self._block_count = block_count
    self._frames = None
    self._generate_frames()
    self._icon_set = None
    self._generate_icons()

  @classmethod
  def blank_block(cls):
    data = codecs.decode('00'*BLOCK_SIZE, 'hex')
    block_count = 0
    return cls(data, block_count)

  def _frame_generator(self):
    frame = 0
    while frame < 64:
      yield self._block_data[frame*FRAME_SIZE:(frame+1)*FRAME_SIZE]
      frame += 1

  def _generate_frames(self):
    self._frames = [
      Frame(frame_data) for frame_data in self._frame_generator()
    ]

  def _generate_icons(self):
    raw_color_palette = self._frames[0]._frame_data[0x60:0x80]
    number_of_icons = self._frames[0]._frame_data[0x02] & 0b1111
    icon_set = IconSet(raw_color_palette)
    icons_frames = self._frames[1:(1+number_of_icons)]
    for icon_frame in icons_frames:
      icon_set.generate_icon_from_data(icon_frame._frame_data)
    self._icon_set = icon_set


class Frame:
  def __init__(self, frame_data):
    self._frame_data = frame_data


class DirectoryHeaderFrame(Frame):
  def __init__(self, frame_data):
    self._frame_data = frame_data
    self._validate_data()

  def _validate_data(self):
    if self._frame_data != self._get_expected_header():
      raise Exception('Invalid Header.')

  def _get_expected_header(self):
    return b"MC" + struct.pack('125s', b'') + struct.pack('B', 0x0E)

  def make_binary(self):
    return self._get_expected_header()


class DirectoryFrame(Frame):
  def __init__(self, frame_data):
    self._frame_data = frame_data
    self._block_state = struct.unpack('I', frame_data[:0x04])[0]
    self._block_size = struct.unpack('I', frame_data[0x04:0x08])[0]
    self._next_block = struct.unpack('H', frame_data[0x08:0x0A])[0]
    self._game_id = self._filter_ascii_chars(frame_data[0x0A:0x1F])

  def _parse_directory_frame(self):
    return {
      'game_id': self._game_id,
      'block_state': self._block_state,
      'block_count': self._block_size//BLOCK_SIZE,
      'next_block_pointer': self._next_block,
    }

  def _filter_ascii_chars(self, raw_bytes):
    filtered_list = [char for char in list(raw_bytes) if 32 <= char <= 126]
    return ''.join([chr(char) for char in filtered_list])

  def make_binary(self):
    block_state = struct.pack('I', self._block_state)
    block_size = struct.pack('I', self._block_size)
    next_block = struct.pack('H', self._next_block)
    game_title = struct.pack('20s', self._game_id.encode())
    filler = struct.pack('97s', b'')
    binary_frame = block_state + block_size + next_block + game_title + filler
    checksum_byte = reduce(lambda b1, b2: b1 ^ b2, binary_frame)
    return binary_frame + struct.pack('B', checksum_byte)


if __name__ == "__main__":
  #path = "data/ff-vii.mcd"
  path = "data/mixed_data.mcd"
  #path = "data/a.mc"
  mc = MemoryCard(path)
  block_number = 12
  mc.delete_block_number(block_number)
  print(mc.get_block_title(block_number))
  mc.plot_icons_for_block(block_number)
