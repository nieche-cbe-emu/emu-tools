
import Foundation
import CoreText
import CoreGraphics

let asciiW = 6, asciiH = 12
let hanziW = 12, hanziH = 12

func rasterize(_ s: String, _ w: Int, _ h: Int, font: CTFont) -> [UInt8] {
    let bpr = (w + 7) / 8
    var out = [UInt8](repeating: 0, count: bpr * h)
    let cs = CGColorSpaceCreateDeviceGray()
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8,
                              bytesPerRow: w, space: cs,
                              bitmapInfo: CGImageAlphaInfo.none.rawValue) else { return out }
    ctx.setFillColor(gray: 0, alpha: 1)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))

    let attrs: [NSAttributedString.Key: Any] = [
        kCTFontAttributeName as NSAttributedString.Key: font,
        kCTForegroundColorAttributeName as NSAttributedString.Key:
            CGColor(gray: 1, alpha: 1)]
    let line = CTLineCreateWithAttributedString(
        NSAttributedString(string: s, attributes: attrs))
    let bounds = CTLineGetBoundsWithOptions(line, .useOpticalBounds)

    let x = (CGFloat(w) - bounds.width) / 2 - bounds.origin.x
    let y = (CGFloat(h) - bounds.height) / 2 - bounds.origin.y
    ctx.textPosition = CGPoint(x: x.rounded(), y: y.rounded())
    CTLineDraw(line, ctx)
    guard let data = ctx.data else { return out }
    let px = data.bindMemory(to: UInt8.self, capacity: w * h)
    for row in 0..<h {

        let src = row * w
        for col in 0..<w where px[src + col] >= 110 {
            out[row * bpr + col / 8] |= UInt8(0x80 >> (col % 8))
        }
    }
    return out
}

func pickFont(_ size: CGFloat, names: [String]) -> CTFont {
    for n in names {
        let f = CTFontCreateWithName(n as CFString, size, nil)
        if (CTFontCopyFullName(f) as String).isEmpty == false { return f }
    }
    return CTFontCreateWithName("Menlo" as CFString, size, nil)
}

let hanziFont = pickFont(CGFloat(hanziH) - 1,
    names: ["PingFangSC-Regular", "HiraginoSansGB-W3", "STHeitiSC-Light", "Menlo"])
let asciiFont = pickFont(CGFloat(asciiH) - 2,
    names: ["Menlo-Regular", "Monaco", "Courier"])
FileHandle.standardError.write("汉字字体: \(CTFontCopyFullName(hanziFont) as String)\n".data(using: .utf8)!)
FileHandle.standardError.write("ASCII 字体: \(CTFontCopyFullName(asciiFont) as String)\n".data(using: .utf8)!)

var out = Data()
out.append(contentsOf: Array("CBEF".utf8))
out.append(contentsOf: [1, 0])
out.append(contentsOf: [UInt8(asciiW), UInt8(asciiH), UInt8(hanziW), UInt8(hanziH)])
func u32(_ v: UInt32) -> [UInt8] { [UInt8(v & 255), UInt8((v >> 8) & 255),
                                    UInt8((v >> 16) & 255), UInt8((v >> 24) & 255)] }
out.append(contentsOf: u32(128))
out.append(contentsOf: u32(94 * 94))

for c in 0..<128 {
    let s = (c >= 32 && c < 127) ? String(UnicodeScalar(UInt8(c))) : " "
    out.append(contentsOf: rasterize(s, asciiW, asciiH, font: asciiFont))
}

let bpr = (hanziW + 7) / 8
let blank = [UInt8](repeating: 0, count: bpr * hanziH)
var filled = 0
for hi in 0..<94 {
    for lo in 0..<94 {
        let gb = Data([UInt8(0xA1 + hi), UInt8(0xA1 + lo)])
        if let s = String(data: gb, encoding: String.Encoding(
                rawValue: CFStringConvertEncodingToNSStringEncoding(
                    CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue)))),
           let ch = s.unicodeScalars.first, ch.value > 0x7F {
            out.append(contentsOf: rasterize(s, hanziW, hanziH, font: hanziFont))
            filled += 1
        } else {
            out.append(contentsOf: blank)
        }
    }
}
FileHandle.standardError.write("汉字槽位已填 \(filled)/\(94*94)\n".data(using: .utf8)!)
let path = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "assets/font12.cbef"
try out.write(to: URL(fileURLWithPath: path))
FileHandle.standardError.write("写出 \(path)，\(out.count) 字节\n".data(using: .utf8)!)
