# Support for OpenPrintTag (CBOR + NDEF)
#
# Copyright (C) 2026 Florian Stamer <florian@stamer.dev>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging
import struct

class CBORDecoder:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def decode(self):
        if self.pos >= len(self.data):
            return None
        
        byte = self.data[self.pos]
        self.pos += 1
        major = byte >> 5
        additional = byte & 0x1F

        if major == 0: # unsigned integer
            return self._decode_uint(additional)
        elif major == 1: # negative integer
            return -1 - self._decode_uint(additional)
        elif major == 2: # byte string
            length = self._decode_uint(additional)
            res = self.data[self.pos:self.pos+length]
            self.pos += length
            return res
        elif major == 3: # text string
            length = self._decode_uint(additional)
            res = self.data[self.pos:self.pos+length].decode("utf-8", "ignore")
            self.pos += length
            return res
        elif major == 4: # array
            length = self._decode_uint(additional)
            return [self.decode() for _ in range(length)]
        elif major == 5: # map
            length = self._decode_uint(additional)
            res = {}
            for _ in range(length):
                key = self.decode()
                val = self.decode()
                if key is not None:
                    res[key] = val
            return res
        elif major == 6: # tag
            self._decode_uint(additional) # skip tag
            return self.decode()
        elif major == 7: # float/simple
            if additional == 20: return False
            if additional == 21: return True
            if additional == 22: return None
            if additional == 26: # float32
                res = struct.unpack(">f", self.data[self.pos:self.pos+4])[0]
                self.pos += 4
                return res
            if additional == 27: # float64
                res = struct.unpack(">d", self.data[self.pos:self.pos+8])[0]
                self.pos += 8
                return res
            if additional < 24: return additional
        
        return None

    def _decode_uint(self, additional):
        if additional < 24:
            return additional
        elif additional == 24:
            res = self.data[self.pos]
            self.pos += 1
            return res
        elif additional == 25:
            res = (self.data[self.pos] << 8) | self.data[self.pos+1]
            self.pos += 2
            return res
        elif additional == 26:
            res = (self.data[self.pos] << 24) | (self.data[self.pos+1] << 16) | \
                  (self.data[self.pos+2] << 8) | self.data[self.pos+3]
            self.pos += 4
            return res
        elif additional == 27:
            res = struct.unpack(">Q", self.data[self.pos:self.pos+8])[0]
            self.pos += 8
            return res
        return 0

class OPTDecoder:
    # Material Type ID mapping from OpenPrintTag spec v1
    MATERIAL_TYPES = {
        0: "GENERIC",
        1: "PLA",
        2: "PETG",
        3: "ABS",
        4: "ASA",
        5: "PA",
        6: "PC",
        7: "TPU",
        8: "PVA",
        9: "HIPS",
        10: "PP",
        11: "FLEX",
        12: "PET",
    }

    def __init__(self):
        pass

    def parse_ndef(self, data):
        # Find NDEF Message TLV (03)
        pos = 0
        while pos < len(data):
            if data[pos] == 0x03: # NDEF Tag
                pos += 1
                length = data[pos]
                if length == 0xFF:
                    length = (data[pos+1] << 8) | data[pos+2]
                    pos += 3
                else:
                    pos += 1
                break
            pos += 1
        else:
            return None

        # Parse NDEF record (MIME type support)
        if pos >= len(data): return None
        header = data[pos]
        pos += 1
        sr = (header >> 4) & 0x01
        type_len = data[pos]
        pos += 1
        
        if sr:
            payload_len = data[pos]
            pos += 1
        else:
            payload_len = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            
        type_name = data[pos:pos+type_len].decode("utf-8", "ignore")
        pos += type_len
        
        if "openprinttag" in type_name.lower():
            return data[pos:pos+payload_len]
            
        return None

    def decode(self, raw_data):
        payload = self.parse_ndef(raw_data)
        if not payload:
            payload = raw_data
            
        try:
            decoder = CBORDecoder(payload)
            full_data = {}
            while decoder.pos < len(payload):
                obj = decoder.decode()
                if isinstance(obj, dict):
                    full_data.update(obj)
                else:
                    break
            return full_data
        except Exception as e:
            logging.error(f"OPT: Failed to decode CBOR: {e}")
            return None

    def map_to_mms(self, opt_data):
        if not isinstance(opt_data, dict) or not opt_data:
            return None
            
        # 1. Name (Key 10)
        name = str(opt_data.get(10) or opt_data.get("name", "Unknown"))
        
        # 2. Vendor (Key 11)
        vendor = str(opt_data.get(11) or opt_data.get("vendor", "Generic"))
        
        # 3. Material (Key 9)
        mat_id = opt_data.get(9)
        material = self.MATERIAL_TYPES.get(mat_id)
        
        # Heuristic Backup: If ID is missing or 0, check name for keywords
        if not material or material == "GENERIC":
            name_u = name.upper()
            if "PETG" in name_u: material = "PETG"
            elif "PLA" in name_u: material = "PLA"
            elif "ABS" in name_u: material = "ABS"
            elif "ASA" in name_u: material = "ASA"
            elif "TPU" in name_u: material = "TPU"
            else: material = material or "PETG"
        
        # 4. Color (Key 64)
        color = "607D8B"
        color_map = opt_data.get(64)
        if isinstance(color_map, dict):
            if color_map.get(0) == 0: # sRGB
                val = color_map.get(1)
                if isinstance(val, (bytes, bytearray)) and len(val) >= 3:
                    color = val[:3].hex().upper()
                elif isinstance(val, list) and len(val) >= 3:
                    color = "".join([f"{c:02X}" for c in val[:3]])
        
        res = {
            "vendor_name": vendor,
            "name": name,
            "filament_material_type": material,
            "color_code": color,
        }
        
        # Temps (37=bed, 34=nozzle)
        try:
            bt = opt_data.get(37)
            if bt is not None: res["bed_temperature"] = float(bt[0]) if isinstance(bt, list) else float(bt)
            
            nt = opt_data.get(34)
            if nt is not None: res["nozzle_temp"] = float(nt[0]) if isinstance(nt, list) else float(nt)
        except Exception:
            pass

        return res
