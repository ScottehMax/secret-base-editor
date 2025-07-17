import struct
from copy import deepcopy
from hashlib import md5
from io import BytesIO
from enum import IntEnum

from baseinfo import BASE_NAMES, BASE_NAMES_REV
from decors import DECORATIONS
from items import ITEMS
from pokemon import MOVES, POKEMON


class Language(IntEnum):
    NONE = 0
    JAPANESE = 1
    ENGLISH = 2
    FRENCH = 3
    ITALIAN = 4
    GERMAN = 5
    KOREAN = 6  # unused
    SPANISH = 7


PARTY_SIZE = 6
MAX_MON_MOVES = 4

SAVE_SIZE = 57344
SAVE_A_OFFSET = 0x0
SAVE_B_OFFSET = 0xE000

SECTION_SIZE = 3968
SECTION_SKIP = 116 # bytes


class Section:
    def __init__(self, data, section_id, checksum, signature, save_index):
        self.data = data
        self.section_id = section_id
        self.checksum = checksum
        self.signature = signature
        self.save_index = save_index

    def __bytes__(self):
        return (
            self.data
            + b'\x00' * (SECTION_SKIP)
            + struct.pack("<H", self.section_id)
            + struct.pack("<H", self.checksum)
            + struct.pack("<I", self.signature)
            + struct.pack("<I", self.save_index)
        )

    def has_valid_checksum(self):
        data = BytesIO(self.data)
        checksum = checksum_block(data, self.section_id)
        return checksum == self.checksum

    def fix_checksum(self):
        data = BytesIO(self.data)
        checksum = checksum_block(data, self.section_id)
        self.checksum = checksum


class HalfSave:
    def __init__(self, sections: list[Section]):
        self.sections = sections

    def __bytes__(self):
        return b"".join(bytes(section) for section in self.sections)


class FullSave:
    def __init__(self, save_a: HalfSave, save_b: HalfSave, extra_sections: bytes):
        self.save_a = save_a
        self.save_b = save_b
        self.extra_sections = extra_sections
        self.active = which_save(save_a, save_b)

    def get_active(self):
        return self.save_a if self.active == 'A' else self.save_b

    def __bytes__(self):
        return bytes(self.save_a) + bytes(self.save_b) + self.extra_sections


def read_section(f):
    data = f.read(SECTION_SIZE)
    f.read(SECTION_SKIP)
    section_id = struct.unpack("<H", f.read(2))[0]
    checksum = struct.unpack("<H", f.read(2))[0]
    signature = struct.unpack("<I", f.read(4))[0]
    save_index = struct.unpack("<I", f.read(4))[0]

    return Section(data, section_id, checksum, signature, save_index)


SECTION_COUNT = 14


def read_save(f):
    sections = []
    for i in range(SECTION_COUNT):
        sections.append(read_section(f))
    return HalfSave(sections)


def read_extra_sections(f):
    res = f.read(4096*4)
    return res


def decoration_xy_to_index(x, y):
    return (x - 7) * 16 + (y - 7)


def index_to_decoration_xy(index):
    x = (index // 16) + 7
    y = (index % 16) + 7
    return x, y


def layout_hash(base):
    # 8 byte hash of all the decorations + their positions
    decors = base['decorations']
    positions = base['decoration_positions']
    decors = [DECORATIONS.index(x) for x in decors]
    positions = [decoration_xy_to_index(x, y) for x, y in positions]
    return md5(bytes(decors + positions)).hexdigest()[0:16]


def team_hash(base):
    # 8 byte hash of the team
    team = base['party']
    team = [
        [
            int(mon['personality'], 16) if isinstance(mon['personality'], str) else mon['personality'],
            POKEMON.index(mon['species']),
            ITEMS.index(mon['held_item']),
            mon['level'],
            mon['evs'],
            *[
                MOVES.index(move)
                for move in mon['moves']
            ]
        ]
        for mon in team
    ]
    team = [item for sublist in team for item in sublist]
    bytes = struct.pack("<" + "IHHBBHHHH" * 6, *team)
    return md5(bytes).hexdigest()[0:16]


cs_byte = [
    3884, 3968, 3968, 3968,
    3848, 3968, 3968, 3968,
    3968, 3968, 3968, 3968,
    3968, 2000
]


def checksum_block(f, idx):
    checksum = 0
    read = 0
    while True:
        data = f.read(4)
        if not data or read >= cs_byte[idx]:
            break
        checksum += struct.unpack("<I", data)[0]
        checksum = (checksum & 0xFFFFFFFF)
        read += 4
    result = (checksum & 0xFFFF) + (checksum >> 16)
    return result & 0xFFFF


def read_party(f):
    party = [{} for _ in range(PARTY_SIZE)]
    for i in range(PARTY_SIZE):
        personality = struct.unpack("<I", f.read(4))[0]
        party[i]["personality"] = f"{personality:X}".zfill(8)
    for i in range(PARTY_SIZE):
        moves = [struct.unpack("<H", f.read(2))[0] for _ in range(MAX_MON_MOVES)]
        try:
            moves = [MOVES[move] for move in moves]
        except:
            pass
        party[i]["moves"] = moves
    for i in range(PARTY_SIZE):
        species = struct.unpack("<H", f.read(2))[0]
        party[i]["species"] = POKEMON[species]
    for i in range(PARTY_SIZE):
        held_item = ITEMS[struct.unpack("<H", f.read(2))[0]]
        party[i]["held_item"] = held_item
    for i in range(PARTY_SIZE):
        level = struct.unpack("<B", f.read(1))[0]#
        party[i]["level"] = level
    for i in range(PARTY_SIZE):
        evs = struct.unpack("<B", f.read(1))[0]
        party[i]["evs"] = evs
    return party


def export_party(party: dict) -> bytes:
    data = b""
    for mon in party:
        data += struct.pack("<I", int(mon["personality"], 16))
    for mon in party:
        for move in mon["moves"]:
            try:
                data += struct.pack("<H", MOVES.index(move))
            except:
                data += struct.pack("<H", MOVES.index('None'))
    for mon in party:
        data += struct.pack("<H", POKEMON.index(mon["species"]))
    for mon in party:
        data += struct.pack("<H", ITEMS.index(mon["held_item"]))
    for mon in party:
        data += struct.pack("<B", mon["level"])
    for mon in party:
        data += struct.pack("<B", mon["evs"])
    return data


ENCODING_TABLE = [
    # 0x00-0x0F
    " ", "À", "Á", "Â", "Ç", "È", "É", "Ê", "Ë", "Ì", " ", "Î", "Ï", "Ò", "Ó", "Ô",
    # 0x10-0x1F
    "Œ", "Ù", "Ú", "Û", "Ñ", "ß", "à", "á", "ね", "ç", "è", "é", "ê", "ë", "ì", " ",
    # 0x20-0x2F
    "î", "ï", "ò", "ó", "ô", "œ", "ù", "ú", "û", "ñ", "º", "ª", "ᵉʳ", "&", "+", " ",
    # 0x30-0x3F
    " ", " ", " ", " ", "Lv", "=", ";", " ", " ", " ", " ", " ", " ", " ", " ", " ",
    # 0x40-0x4F
    " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ",
    # 0x50-0x5F
    "▯", "¿", "¡", "PK", "MN", "PO", "Ké", "BL", "OC", "K_", "Í", "%", "(", ")", " ", " ",
    # 0x60-0x6F
    " ", " ", " ", " ", " ", " ", " ", " ", "â", " ", " ", " ", " ", " ", " ", "í",
    # 0x70-0x7F
    " ", " ", " ", " ", " ", " ", " ", " ", " ", "⬆", "⬇", "⬅", "➡", " ", " ", " ",
    # 0x80-0x8F
    " ", " ", " ", " ", "ᵉ", "<", ">", " ", " ", " ", " ", " ", " ", " ", " ", " ",
    # 0x90-0x9F
    " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ",
    # 0xA0-0xAF
    "ʳᵉ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", ".", "-", "・",
    # 0xB0-0xBF
    "…", '“', "”", "‘", "’", "♂", "♀", "$", ",", "×", "/", "A", "B", "C", "D", "E",
    # 0xC0-0xCF
    "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
    # 0xD0-0xDF
    "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k",
    # 0xE0-0xEF
    "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "▶",
    # 0xF0-0xFF
    ":", "Ä", "Ö", "Ü", "ä", "ö", "ü", " ", " ", " ", " ", " ", " ", " ", " ", " ",
]

ENCODING_TABLE_JP = [
    " ", "あ", "い", "う", "え", "お", "か", "き", "く", "け", "こ", "さ", "し", "す", "せ", "そ",
    "た", "ち", "つ", "て", "と", "な", "に", "ぬ", "ね", "の", "は", "ひ", "ふ", "へ", "ほ", "ま",
    "み", "む", "め", "も", "や", "ゆ", "よ", "ら", "り", "る", "れ", "ろ", "わ", "を", "ん", "ぁ",
    "ぃ", "ぅ", "ぇ", "ぉ", "ゃ", "ゅ", "ょ", "が", "ぎ", "ぐ", "げ", "ご", "ざ", "じ", "ず", "ぜ",
    "ぞ", "だ", "ぢ", "づ", "で", "ど", "ば", "び", "ぶ", "べ", "ぼ", "ぱ", "ぴ", "ぷ", "ぺ", "ぽ",
    "っ", "ア", "イ", "ウ", "エ", "オ", "カ", "キ", "ク", "ケ", "コ", "サ", "シ", "ス", "セ", "ソ",
    "タ", "チ", "ツ", "テ", "ト", "ナ", "ニ", "ヌ", "ネ", "ノ", "ハ", "ヒ", "フ", "ヘ", "ホ", "マ",
    "ミ", "ム", "メ", "モ", "ヤ", "ユ", "ヨ", "ラ", "リ", "ル", "レ", "ロ", "ワ", "ヲ", "ン", "ァ",
    "ィ", "ゥ", "ェ", "ォ", "ャ", "ュ", "ョ", "ガ", "ギ", "グ", "ゲ", "ゴ", "ザ", "ジ", "ズ", "ゼ",
    "ゾ", "ダ", "ヂ", "ヅ", "デ", "ド", "バ", "ビ", "ブ", "ベ", "ボ", "パ", "ピ", "プ", "ペ", "ポ",
    "ッ", "０", "１", "２", "３", "４", "５", "６", "７", "８", "９", "！", "？", "。", "ー", "・",
    "‥", "『", "』", "「", "」", "♂", "♀", "円", "．", "×", "／", "Ａ", "Ｂ", "Ｃ", "Ｄ", "Ｅ",
    "Ｆ", "Ｇ", "Ｈ", "Ｉ", "Ｊ", "Ｋ", "Ｌ", "Ｍ", "Ｎ", "Ｏ", "Ｐ", "Ｑ", "Ｒ", "Ｓ", "Ｔ", "Ｕ",
    "Ｖ", "Ｗ", "Ｘ", "Ｙ", "Ｚ", "ａ", "ｂ", "ｃ", "ｄ", "ｅ", "ｆ", "ｇ", "ｈ", "ｉ", "ｊ", "ｋ",
    "ｌ", "ｍ", "ｎ", "ｏ", "ｐ", "ｑ", "ｒ", "ｓ", "ｔ", "ｕ", "ｖ", "ｗ", "ｘ", "ｙ", "ｚ", "►",
    "：", "Ä", "Ö", "Ü", "ä", "ö", "ü", "↑", "↓", "←", " ", " ", " ", " ", " ", " ",
]


PLAYER_NAME_LENGTH = 7
TRAINER_ID_LENGTH = 4
DECOR_MAX_SECRET_BASE = 16
MAP_OFFSET = 7


def decode_text(text, language=Language.ENGLISH):
    if language == Language.JAPANESE:
        table = ENCODING_TABLE_JP
    else:
        table = ENCODING_TABLE
    return "".join(table[c] for c in text)


def encode_text(text, language=Language.ENGLISH):
    if language == Language.JAPANESE:
        table = ENCODING_TABLE_JP
    else:
        table = ENCODING_TABLE
    return bytes(table.index(c) for c in text)


def read_secret_base(f):
    secret_base_id = BASE_NAMES[struct.unpack("<B", f.read(1))[0]]
    info = struct.unpack("<B", f.read(1))[0]

    to_register = info & 0b1111
    gender = (info >> 4) & 0b1
    battled_owner_today = (info >> 5) & 0b1
    registry_status = (info >> 6) & 0b11

    trainer_name_bytes = f.read(PLAYER_NAME_LENGTH)
    trainer_id = f.read(TRAINER_ID_LENGTH)
    ID = str(struct.unpack("<I", trainer_id)[0] & 0xFFFF).zfill(5)
    SID = str(struct.unpack("<I", trainer_id)[0] >> 16).zfill(5)

    language = Language(struct.unpack("<B", f.read(1))[0])
    trainer_name = decode_text(trainer_name_bytes, language).strip()
    num_secret_bases_received = struct.unpack("<H", f.read(2))[0]
    num_times_entered = struct.unpack("<B", f.read(1))[0]
    unused = struct.unpack("<B", f.read(1))[0]
    decorations = struct.unpack("<16B", f.read(16))
    decorations = [DECORATIONS[d] for d in decorations]
    decoration_positions = struct.unpack("<16B", f.read(16))
    decoration_positions = [
        (
            (d >> 4) + MAP_OFFSET,
            (d & 0xF) + MAP_OFFSET
        )
        for d in decoration_positions
    ]
    f.read(2) # padding

    party = read_party(f)

    return {
        "secret_base_id": secret_base_id,
        "to_register": to_register,
        "gender": gender,
        "battled_owner_today": battled_owner_today,
        "registry_status": registry_status,
        "trainer_name": trainer_name,
        "id": ID,
        "sid": SID,
        "language": language,
        "num_secret_bases_received": num_secret_bases_received,
        "num_times_entered": num_times_entered,
        "unused": unused,
        "decorations": decorations,
        "decoration_positions": decoration_positions,
        "party": party
    }


def export_secret_base(secret_base: dict) -> bytes:
    data = b""
    data += struct.pack("<B", BASE_NAMES_REV[secret_base["secret_base_id"]])
    info = (
        secret_base["to_register"]
        | (
            secret_base["gender"] << 4
            | (secret_base["battled_owner_today"] << 5)
            | (secret_base["registry_status"] << 6)
        )
    )
    data += struct.pack("<B", info)
    # print(secret_base['trainer_name'])
    data += encode_text(secret_base["trainer_name"], secret_base["language"]).ljust(PLAYER_NAME_LENGTH, b"\xFF")
    trainer_id = (int(secret_base["sid"]) << 16) | int(secret_base["id"])
    data += struct.pack("<I", trainer_id)

    data += struct.pack("<B", secret_base["language"])
    data += struct.pack("<H", secret_base["num_secret_bases_received"])
    data += struct.pack("<B", secret_base["num_times_entered"])
    data += struct.pack("<B", secret_base["unused"])
    decoration_ids = [DECORATIONS.index(d) for d in secret_base["decorations"]]
    # print(decoration_ids, secret_base["decorations"])
    data += struct.pack("<16B", *decoration_ids)
    decoration_positions = [
        (x - MAP_OFFSET) << 4 | (y - MAP_OFFSET)
        for x, y in secret_base["decoration_positions"]
    ]
    data += struct.pack("<16B", *decoration_positions)
    data += b"\x00\x00" # padding

    data += export_party(secret_base["party"])

    return data


def which_save(a, b):
    # determine which save index is higher
    a_index = a.sections[0].save_index
    b_index = b.sections[0].save_index

    if a_index > b_index:
        return 'A'
    else:
        return 'B'


def load_full_save(path) -> FullSave:
    with open(path, "rb") as f:
        save_a = read_save(f)
        save_b = read_save(f)
        extra = read_extra_sections(f)

    save = FullSave(save_a, save_b, extra)
    return save


def load_save(path) -> HalfSave:
    with open(path, "rb") as f:
        save_a = read_save(f)
        save_b = read_save(f)

    print('Using save ' + which_save(save_a, save_b))

    if which_save(save_a, save_b) == 'A':
        save = save_a
    else:
        save = save_b

    return save


def get_base_from_save(save):
    for section in save.sections:
        data = BytesIO(section.data)
        checksum = checksum_block(data, section.section_id)

        if checksum != section.checksum:
            print("Checksum failed for section", section.section_id)
            print("Expected", section.checksum, "but got", checksum)
            continue

        if section.section_id == 3:
            data = BytesIO(section.data[0x77C:])
            secret_base = read_secret_base(data)

            return secret_base


def getVersion(save):
    version = None

    # The save index value is the same across all sections.
    save_index = save.sections[0].save_index

    # Find where section section 0 is using the save index and extract the game code.
    gameCode = int(save.sections[save_index % 14].data[172:176][0])

    match gameCode:
        case 0:
            version = 'ruby/sapphire'
        case 1:
            version = 'firered/leafgreen'
        case _:
            version = 'emerald'

    return version


def get_all_bases_from_save(save, version):
    bases = []
    split_base = b''
    save_index = save.sections[0].save_index

    # Secret Base data is split between sections 2 and 3.
    sections = []
    sections.append(save.sections[(save_index + 2) % 14])
    sections.append(save.sections[(save_index + 3) % 14])

    # Account for save file differences between emerald and ruby/sapphire.
    if version == 'emerald':
        section_2_start = 0xB1C
        base_8_start = 0xF7C
        section_2_end = 4
        section_3_start = 156
        section_3_cont = 0x9C
    else:
        section_2_start = 0xA88
        base_8_start = 0xEE8
        section_2_end = 152
        section_3_start = 8
        section_3_cont = 0x8

    for section in sections:
        data = BytesIO(section.data)
        try:
            checksum = checksum_block(data, section.section_id)
            if checksum != section.checksum:
                print("Checksum failed for section", section.section_id)
                print("Expected", section.checksum, "but got", checksum)
                continue
        except:
            print("Checksum failed for section", section.section_id)
            pass

        match section.section_id:
            case 2:
                for i in range(7):
                    data = BytesIO(section.data[section_2_start + (160*i):])
                    secret_base = read_secret_base(data)
                    bases.append(secret_base)

                # The eight secret base data is split between the sections.
                split_base += section.data[base_8_start:base_8_start+section_2_end]
            case 3:
                split_base += section.data[0:section_3_start]
                data = BytesIO(split_base)
                secret_base = read_secret_base(data)
                bases.append(secret_base)

                for i in range(12):
                    data = BytesIO(section.data[section_3_cont + (160*i):])
                    secret_base = read_secret_base(data)
                    bases.append(secret_base)
            case _:
                print("Wrong save file section.")

    return bases


def insert_base_to_section(section, secret_base, index):
    if index < 8:
        section.data = section.data[:0xB1C + (160*index)] + export_secret_base(secret_base) + section.data[0xB1C + (160*index) + len(export_secret_base(secret_base)):]
    else:
        section.data = section.data[:0x9C + (160*(index-8))] + export_secret_base(secret_base) + section.data[0x9C + (160*(index-8)) + len(export_secret_base(secret_base)):]
    section.fix_checksum()
    return section


def insert_split_base_to_section(s2, s3, secret_base):
    # index isn't necessary since it's always 8
    data = export_secret_base(secret_base)
    s2.data = s2.data[:0xF7C] + data[:4] + s2.data[0xF7C+4:]
    s3.data = data[4:] + s3.data[156:]
    s2.fix_checksum()
    s3.fix_checksum()
    return s2, s3


def insert_base_to_save(base_save, secret_base, index):
    save = deepcopy(base_save)
    i = 0
    s2idx, s3idx = None, None

    for i in range(len(save.sections)):
        section = save.sections[i]

        if index < 7 and section.section_id == 2:
            section = insert_base_to_section(section, secret_base, index)
        if index >= 8 and section.section_id == 3:
            section = insert_base_to_section(section, secret_base, index)

        if index == 7:
            if section.section_id == 2:
                s2idx = i
            if section.section_id == 3:
                s3idx = i

        save.sections[i] = section

    if index == 7:
        # really annoying
        s2, s3 = insert_split_base_to_section(save.sections[s2idx], save.sections[s3idx], secret_base)
        save.sections[s2idx] = s2
        save.sections[s3idx] = s3

    return save


def insert_halfsave_to_save(base_save, half_save) -> FullSave:
    save = deepcopy(base_save)
    if which_save(save.save_a, save.save_b) == 'A':
        save.save_a = half_save
    else:
        save.save_b = half_save
    return save
