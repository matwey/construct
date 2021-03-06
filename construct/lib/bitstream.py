from time import sleep



class RestreamedBytesIO:
    __slots__ = ["substream", "encoder", "encoderunit", "decoder", "decoderunit", "rbuffer", "wbuffer","sincereadwritten"]

    def __init__(self, substream, encoder, encoderunit, decoder, decoderunit):
        self.substream = substream
        self.encoder = encoder
        self.encoderunit = encoderunit
        self.decoder = decoder
        self.decoderunit = decoderunit
        self.rbuffer = b""
        self.wbuffer = b""
        self.sincereadwritten = 0

    def read(self, count):
        if count < 0:
            raise ValueError("count cannot be negative")
        while len(self.rbuffer) < count:
            self.rbuffer += self.decoder(self.substream.read(self.decoderunit))
        data, self.rbuffer = self.rbuffer[:count], self.rbuffer[count:]
        self.sincereadwritten += count
        return data

    def write(self, data):
        self.wbuffer += data
        datalen = len(data)
        while len(self.wbuffer) >= self.encoderunit:
            data, self.wbuffer = self.wbuffer[:self.encoderunit], self.wbuffer[self.encoderunit:]
            self.substream.write(self.encoder(data))
        self.sincereadwritten += datalen
        return datalen

    def close(self):
        if len(self.rbuffer):
            raise ValueError("closing stream but %d unread bytes remain, %d is decoded unit" % (len(self.rbuffer), self.decoderunit))
        if len(self.wbuffer):
            raise ValueError("closing stream but %d unwritten bytes remain, %d is encoded unit" % (len(self.wbuffer), self.encoderunit))

    def seekable(self):
        return False

    def tell(self):
        """WARNING: tell is correct only on read-only and write-only instances."""
        return self.sincereadwritten

    def tellable(self):
        return True




class RebufferedBytesIO:
    __slots__ = ["substream","offset","rwbuffer","moved","tailcutoff"]

    def __init__(self, substream, tailcutoff=None):
        self.substream = substream
        self.offset = 0
        self.rwbuffer = b""
        self.moved = 0
        self.tailcutoff = tailcutoff

    def read(self, count):
        startsat = self.offset
        endsat = startsat + count
        if startsat < self.moved:
            raise IOError("could not read because tail was cut off")
        while self.moved + len(self.rwbuffer) < endsat:
            newdata = self.substream.read(128*1024)
            self.rwbuffer += newdata
            if not newdata:
                sleep(0)
        data = self.rwbuffer[startsat-self.moved:endsat-self.moved]
        self.offset += count
        if self.tailcutoff is not None and self.moved < self.offset - self.tailcutoff:
            removed = self.offset - self.tailcutoff - self.moved
            self.moved += removed
            self.rwbuffer = self.rwbuffer[removed:]
        if len(data) < count:
            raise IOError("could not read enough bytes, something went wrong")
        return data

    def write(self, data):
        startsat = self.offset
        endsat = startsat + len(data)
        while self.moved + len(self.rwbuffer) < startsat:
            newdata = self.substream.read(128*1024)
            self.rwbuffer += newdata
            if not newdata:
                sleep(0)
        self.rwbuffer = self.rwbuffer[:startsat-self.moved] + data + self.rwbuffer[endsat-self.moved:]
        self.offset = endsat
        if self.tailcutoff is not None and self.moved < self.offset - self.tailcutoff:
            removed = self.offset - self.tailcutoff - self.moved
            self.moved += removed
            self.rwbuffer = self.rwbuffer[removed:]
        return len(data)

    def seek(self, at, whence=0):
        if whence == 0:
            self.offset = at
            return self.offset
        elif whence == 1:
            self.offset += at
            return self.offset
        else:
            raise ValueError("seeks only with whence 0 and 1")

    def seekable(self):
        return True

    def tell(self):
        return self.offset

    def tellable(self):
        return True

    def cachedfrom(self):
        return self.moved

    def cachedto(self):
        return self.moved + len(self.rwbuffer)


