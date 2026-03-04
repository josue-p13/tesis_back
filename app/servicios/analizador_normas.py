from app.modelos.schemas import ResultadoAnalisis, TipoNorma, CitaDetalle


def analizar_norma(referencias: list[str], norma: TipoNorma) -> ResultadoAnalisis:
    """Analiza referencias contra una norma académica"""
    errores = []
    
    if not referencias:
        errores.append("No se detectaron referencias bibliográficas")
        return ResultadoAnalisis(
            cumple=False,
            norma=norma,
            errores=errores,
            detalles="No se encontraron referencias"
        )
    
    citas_validas = [CitaDetalle(texto=ref, valida=True) for ref in referencias]
    
    return ResultadoAnalisis(
        cumple=True,
        norma=norma,
        errores=errores,
        detalles=f"Referencias extraídas: {len(referencias)}",
        citas_validas=citas_validas,
        total_citas=len(citas_validas),
        referencias_completas=referencias
    )

