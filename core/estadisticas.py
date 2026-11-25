"""Cálculos estadísticos compartidos por el panel y los centros de sección."""

from .models import Equipo


def tabla_posiciones(campeonato):
    """Clasificación de un campeonato calculada con los goles registrados.

    Solo intervienen partidos con marcador completo. Los equipos inscritos sin
    partidos jugados aparecen con todos sus contadores en cero.
    """
    equipos = {}
    for equipo in Equipo.objects.filter(
        inscripcion__campeonato=campeonato
    ).distinct():
        equipos[equipo.pk] = {
            'equipo': equipo,
            'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
            'gf': 0, 'gc': 0, 'dg': 0, 'pts': 0,
        }

    partidos = campeonato.partido_set.select_related(
        'equipo_local', 'equipo_visitante'
    ).filter(goles_local__isnull=False, goles_visitante__isnull=False)

    # Recorrido con while: se materializa la consulta y se avanza por índice.
    lista_partidos = list(partidos)
    indice = 0
    while indice < len(lista_partidos):
        partido = lista_partidos[indice]
        indice += 1

        local = equipos.setdefault(partido.equipo_local_id, {
            'equipo': partido.equipo_local,
            'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
            'gf': 0, 'gc': 0, 'dg': 0, 'pts': 0,
        })
        visitante = equipos.setdefault(partido.equipo_visitante_id, {
            'equipo': partido.equipo_visitante,
            'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
            'gf': 0, 'gc': 0, 'dg': 0, 'pts': 0,
        })
        gl, gv = partido.goles_local, partido.goles_visitante
        local['pj'] += 1
        visitante['pj'] += 1
        local['gf'] += gl
        local['gc'] += gv
        visitante['gf'] += gv
        visitante['gc'] += gl
        if gl > gv:
            local['pg'] += 1
            visitante['pp'] += 1
            local['pts'] += 3
        elif gl < gv:
            visitante['pg'] += 1
            local['pp'] += 1
            visitante['pts'] += 3
        else:
            local['pe'] += 1
            visitante['pe'] += 1
            local['pts'] += 1
            visitante['pts'] += 1

    filas = list(equipos.values())
    for fila in filas:
        fila['dg'] = fila['gf'] - fila['gc']
    filas.sort(key=lambda f: (-f['pts'], -f['dg'], -f['gf'], f['equipo'].nombre))
    return filas
