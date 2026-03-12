#!/usr/bin/env python3
"""
Script para inspeccionar el XML real que devuelve GROBID
Modificará temporalmente el parser para guardar el XML
"""
import sys
sys.path.insert(0, '/home/josue/Escritorio/Tesis/back_def')

from app.services.obtener.xml_parser_service import parsear_referencias_xml

# Simular un XML típico de GROBID
xml_ejemplo = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader/>
    <text>
        <div>
            <listBibl>
                <biblStruct>
                    <note type="raw_reference">Smith, J. (2024) A comprehensive guide. Journal of AI, 15(3), pp. 45-67.</note>
                    <analytic>
                        <title type="main">A comprehensive guide</title>
                        <author>
                            <persName>
                                <forename>J</forename>
                                <surname>Smith</surname>
                            </persName>
                        </author>
                    </analytic>
                    <monogr>
                        <title>Journal of AI</title>
                        <imprint>
                            <date type="published" when="2024"/>
                            <biblScope unit="volume">15</biblScope>
                            <biblScope unit="page" from="45" to="67"/>
                        </imprint>
                    </monogr>
                </biblStruct>
            </listBibl>
        </div>
    </text>
</TEI>
"""

print("=" * 80)
print("PRUEBA: ¿El parser extrae el campo 'raw'?")
print("=" * 80)

referencias = parsear_referencias_xml(xml_ejemplo)

print(f"\nTotal referencias extraídas: {len(referencias)}")

for i, ref in enumerate(referencias, 1):
    print(f"\n[{i}] Campos extraídos:")
    for campo, valor in ref.items():
        print(f"  {campo}: {valor}")
    
    if 'raw' in ref:
        print(f"\n✅ Campo 'raw' encontrado: {ref['raw']}")
    else:
        print(f"\n❌ Campo 'raw' NO encontrado")

print("\n" + "=" * 80)
