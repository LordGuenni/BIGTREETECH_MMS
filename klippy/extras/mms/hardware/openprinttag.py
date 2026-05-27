# Support for OpenPrintTag (CBOR + NDEF)
#
# Copyright (C) 2026 Florian Stamer <florian@stamer.dev>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging

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
            res = self.data[self.pos:self.pos+length].decode("utf-8")
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
                import struct
                res = struct.unpack(">f", self.data[self.pos:self.pos+4])[0]
                self.pos += 4
                return res
            if additional == 27: # float64
                import struct
                res = struct.unpack(">d", self.data[self.pos:self.pos+8])[0]
                self.pos += 8
                return res
        
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
            import struct
            res = struct.unpack(">Q", self.data[self.pos:self.pos+8])[0]
            self.pos += 8
            return res
        return 0

class OPTDecoder:
    # Material Type ID mapping from OpenPrintTag spec
    MATERIAL_TYPES = {
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
        # Very simple NDEF parser for OpenPrintTag
        pos = 0
        while pos < len(data):
            header = data[pos]
            pos += 1
            # MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x02 (Mime)
            sr = (header >> 4) & 0x01
            tnf = header & 0x07
            
            type_len = data[pos]
            pos += 1
            
            if sr:
                payload_len = data[pos]
                pos += 1
            else:
                import struct
                payload_len = struct.unpack(">I", data[pos:pos+4])[0]
                pos += 4
                
            type_name = data[pos:pos+type_len].decode("utf-8", "ignore")
            pos += type_len
            
            payload = data[pos:pos+payload_len]
            pos += payload_len
            
            if "openprinttag" in type_name.lower():
                return payload
                
            if pos >= len(data) or data[pos] == 0xFE: # Terminator
                break
        return None

    def decode(self, raw_data):
        # raw_data is a bytes object from the tag
        # Skip NFC/NDEF headers if needed
        # OpenPrintTag usually starts with NDEF
        payload = self.parse_ndef(raw_data)
        if not payload:
            # Try raw CBOR if NDEF not found (fallback)
            payload = raw_data
            
        try:
            decoder = CBORDecoder(payload)
            return decoder.decode()
        except Exception as e:
            logging.error(f"OPT: Failed to decode CBOR: {e}")
            return None

    def map_to_mms(self, opt_data):
        if not isinstance(opt_data, dict):
            return None
            
        # OpenPrintTag v1 spec uses integer keys
        # 11: brand, 10: name, 9: material_type_id, 34/35: nozzle, 37/38: bed, 64: color
        
        # 1. Vendor
        vendor = opt_data.get(11) or opt_data.get("vendor")
        
        # 2. Product Name
        name = opt_data.get(10) or opt_data.get("name")
        
        # 3. Material
        mat_id = opt_data.get(9) or opt_data.get("material_id")
        material = self.MATERIAL_TYPES.get(mat_id) if mat_id else (opt_data.get("material") or "PETG")
        
        # 4. Color
        color = None
        color_map = opt_data.get(64)
        if isinstance(color_map, dict):
            # Key 0 is space (0=sRGB), Key 1 is value
            if color_map.get(0) == 0:
                val = color_map.get(1)
                if isinstance(val, (bytes, bytearray)) and len(val) >= 3:
                    color = val[:3].hex().upper()
                elif isinstance(val, list) and len(val) >= 3:
                    color = "".join([f"{c:02X}" for c in val[:3]])
        
        if not color:
            color = opt_data.get("color") or "607D8B" # Default gray-blue
            
        res = {
            "vendor_name": vendor,
            "name": name,
            "filament_material_type": material,
            "color_code": color,
        }
        
        # Handle temps
        bt = opt_data.get(37) or opt_data.get("bed_temperature")
        if bt: res["bed_temperature"] = float(bt)
        
        nt = opt_data.get(34) or opt_data.get("printing_temperature")
        if nt: res["nozzle_temp"] = float(nt)

        return res
