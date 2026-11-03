from core.models import Club, Equipo
from datetime import date

datos = [
    {
        "nombre": "Oruro Royal Club",
        "fundacion": date(1896, 5, 26),
        "presidente": "Ing. Ivar Cortez V.",
        "direccion": "Av. 6 de Octubre esq. Sargento Flores s/n, Oruro",
        "telefono": "+591 (2) 525-4190 / 724-81992",
        "categoria_ingreso": "Primera A",
        "estado_juridico": "Homologado FBF",
        "equipos": [
            'Primera "A" (Honor)',
            "Juvenil Sub-19",
            "Femenino Primera",
            "Sub-15 Infantil"
        ]
    },
    {
        "nombre": "C.D. San José de Oruro",
        "fundacion": date(1942, 3, 19),
        "presidente": "Dr. Ernesto Aranibar",
        "direccion": "Calle Washington entre Sucre y Bolívar #1432, Oruro",
        "telefono": "+591 (2) 524-7811 / 718-50021",
        "categoria_ingreso": "Primera A",
        "estado_juridico": "Tribunal Regularizado",
        "equipos": [
            'Primera "A" (Oficial)',
            "Reserva Sub-20",
            "Sub-17 Cantera",
            "Femenino Sub-18"
        ]
    },
    {
        "nombre": "Club Deportivo Sur-Car",
        "fundacion": date(2014, 3, 21),
        "presidente": "Sra. Edgar Zuna G.",
        "direccion": "Calle Pagador entre Herrera y 1ro de Noviembre, Oruro",
        "telefono": "+591 (2) 528-9901 / 741-20934",
        "categoria_ingreso": "Primera A",
        "estado_juridico": "Al Día A.F.O.",
        "equipos": [
            'Primera "A"',
            "Copa Simón Bolívar",
            "Sub-19 Juvenil"
        ]
    },
    {
        "nombre": "Empresa Minera Huanuni",
        "fundacion": date(2012, 2, 2),
        "presidente": "Lic. Pedro Choque M.",
        "direccion": "Plaza Principal Huanuni s/n, Sede Sindicato Minero",
        "telefono": "+591 (2) 552-2109 / 718-44211",
        "categoria_ingreso": "Primera A",
        "estado_juridico": "Vigente",
        "equipos": [
            'Primera "A"',
            "Huanuni Juvenil B",
            "Femenino Minero"
        ]
    },
    {
        "nombre": "Club Deportivo Shalon",
        "fundacion": date(1999, 5, 9),
        "presidente": "Lic. Jaime Montaño L.",
        "direccion": "Calle Cochabamba y La Plata #780, Oruro",
        "telefono": "+591 (2) 527-3312 / 723-11890",
        "categoria_ingreso": "Primera A",
        "estado_juridico": "Vigente A.F.O.",
        "equipos": [
            'Primera "A" (Copa)',
            "Shalon Sub-19"
        ]
    },
    {
        "nombre": "Club Ingenieros de Oruro",
        "fundacion": date(1928, 7, 4),
        "presidente": "Ing. Carlos Morales C.",
        "direccion": "Ciudad Universitaria FNI, Av. Dehene, Oruro",
        "telefono": "+591 (2) 526-1210 / 704-98112",
        "categoria_ingreso": "Primera B",
        "estado_juridico": "Vinculado UTO",
        "equipos": [
            'Primera "B" (Ascenso)',
            "Facultativo UTO",
            "Femenino Honor"
        ]
    }
]

for dato in datos:
    equipos = dato.pop("equipos")

    club, creado = Club.objects.get_or_create(
        nombre=dato["nombre"],
        defaults=dato
    )

    for nombre_equipo in equipos:
        Equipo.objects.get_or_create(
            nombre=nombre_equipo,
            club=club
        )

print("Clubes registrados:", Club.objects.count())
print("Equipos registrados:", Equipo.objects.count())