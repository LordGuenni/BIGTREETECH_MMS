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
    # Material Type ID mapping from official OpenPrintTag spec v1
    MATERIAL_TYPES = {
        0: "PLA",
        1: "PETG",
        2: "ABS",
        3: "ASA",
        4: "PC",
        5: "PP",
        6: "PA",
        7: "TPU",
        8: "HIPS",
        9: "PVA",
        10: "BVOH",
        11: "PVB",
        12: "PET",
    }

    def __init__(self):
        pass

    def parse_ndef(self, data):
        # Find NDEF Message TLV (03)
        pos = 0
        while pos < len(data):
            if data[pos] == 0x03:
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
            
        # Strict mapping according to OpenPrintTag v1 Spec
        # 11: brand_name, 10: material_name, 9: material_type (enum)
        
        vendor = opt_data.get(11)
        name = opt_data.get(10)
        
        mat_id = opt_data.get(9)
        material = self.MATERIAL_TYPES.get(mat_id, "GENERIC")
        
        # Color (Key 19 - color_rgba)
        color = None
        c19 = opt_data.get(19)
        if isinstance(c19, (bytes, bytearray)) and len(c19) >= 3:
            color = c19[:3].hex().upper()
        elif isinstance(c19, list) and len(c19) >= 3:
            color = "".join([f"{c:02X}" for c in c19[:3]])
            
        # Fallback to Key 64 (color map)
        if not color:
            color_map = opt_data.get(64)
            if isinstance(color_map, dict) and color_map.get(0) == 0:
                val = color_map.get(1)
                if isinstance(val, (bytes, bytearray)) and len(val) >= 3:
                    color = val[:3].hex().upper()
        
        if not color:
            color = "607D8B"
        
        # Final result using MMS internal keys
        res = {
            "filament_manufacturer": vendor,
            "filament_type_detailed": name,
            "filament_material_type": material,
            "color_code": color,
        }
        
        # Temps (37: min_bed, 34: min_print)
        try:
            bt = opt_data.get(37)
            if bt is not None: res["bed_temperature"] = float(bt[0]) if isinstance(bt, list) else float(bt)
            
            nt = opt_data.get(34)
            if nt is not None: res["nozzle_temp"] = float(nt[0]) if isinstance(nt, list) else float(nt)
        except Exception:
            pass

        return res
