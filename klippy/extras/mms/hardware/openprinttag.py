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
            
        # OpenPrintTag v1 spec uses integer keys (tags)
        # 1: version, 2: vendor, 10: name, 11: material, 19: color ...
        # Mapping based on openprinttag.org
        res = {
            "vendor_name": opt_data.get(2) or opt_data.get("vendor"),
            "name": opt_data.get(10) or opt_data.get("name"),
            "filament_material_type": opt_data.get(11) or opt_data.get("material"),
            "color_code": opt_data.get(19) or opt_data.get("color"),
        }
        
        # Handle bed/nozzle temps if present
        bt = opt_data.get(34) or opt_data.get("bed_temperature")
        if bt: res["bed_temperature"] = int(bt)
        
        nt = opt_data.get(36) or opt_data.get("printing_temperature")
        if nt: res["nozzle_temp"] = int(nt)

        return res
