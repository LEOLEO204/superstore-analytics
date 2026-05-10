import sys
import re

filepath = r'd:\DATN\docs\DoanHaiXuyen_CNTTVA2_DeCuongDATN.doc'

try:
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Try extracting ASCII and simple latin extended
    ascii_matches = re.findall(b'[a-zA-Z0-9 \(\)\.\,\:\_\-\\\/]{4,}', data)
    
    # Let's try to decode as utf-16-le which is very common in word docs
    try:
        text_utf16 = data.decode('utf-16le', errors='ignore')
        utf16_matches = re.findall(r'[\u0020-\uFFFF]{4,}', text_utf16)
    except:
        utf16_matches = []
        
    # Output everything extracted to a scratch text file
    with open(r'd:\DATN\extracted_doc_content.txt', 'w', encoding='utf-8') as out:
        out.write("--- EXTRACTED ASCII CONTENT ---\n")
        for match in ascii_matches:
            try:
                out.write(match.decode('ascii') + "\n")
            except:
                pass
                
        out.write("\n\n--- EXTRACTED UTF-16 CONTENT ---\n")
        for m in utf16_matches:
            # Filter heavily to remove noise and only keep readable strings
            if any(c.isalpha() for c in m) and len(m.strip()) > 10:
                 out.write(m.strip() + "\n")
                 
    print("Successfully extracted text to extracted_doc_content.txt")
except Exception as e:
    print(f"Error: {e}")
