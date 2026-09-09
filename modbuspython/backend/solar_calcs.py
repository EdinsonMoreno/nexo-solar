"""Solar position calculation utilities for SolarSense SCADA.





This module provides functions for calculating solar position angles




(azimuth and elevation) based on geographic location, date, and time.




Used for automatic solar tracking in the SCADA system.





Requirements validated: Core solar tracking functionality
"""

import math


def calculate_hra(hora_local: float, longitud: float, dia: int) -> float:
    """Calcula el ángulo de hora solar (HRA).





    Args:




        hora_local: Hora local en formato decimal




        longitud: Longitud geográfica en grados




        dia: Día del año (1-365)





    Returns:




        Ángulo de hora solar en grados
    """

    # Ángulo de hora solar (HRA)

    b = 2 * math.pi * (dia - 81) / 364

    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    tc = 4 * (longitud - 15 * 0) + eot  # 0 = huso horario

    hra = 15 * (hora_local + tc / 60 - 12)
    return hra


def calculate_decl(dia: int) -> float:
    """Calcula la declinación solar.





    Args:




        dia: Día del año (1-365)





    Returns:




        Declinación solar en grados
    """

    # Declinación solar

    return 23.45 * math.sin(math.radians(360 * (284 + dia) / 365))


def calculate_alt(latitud: float, decl: float, hra: float) -> float:
    """Calcula el ángulo de elevación solar.





    Args:




        latitud: Latitud geográfica en grados




        decl: Declinación solar en grados




        hra: Ángulo de hora solar en grados





    Returns:




        Ángulo de elevación solar en grados
    """

    # Ángulo de elevación solar
    return math.degrees(
        math.asin(
            math.sin(math.radians(latitud)) * math.sin(math.radians(decl))
            + math.cos(math.radians(latitud)) * math.cos(math.radians(decl)) * math.cos(math.radians(hra))
        )
    )


def calculate_az(latitud: float, decl: float, hra: float, alt: float) -> float:
    """Calcula el ángulo de azimut solar.





    Args:




        latitud: Latitud geográfica en grados




        decl: Declinación solar en grados




        hra: Ángulo de hora solar en grados




        alt: Ángulo de elevación solar en grados





    Returns:




        Ángulo de azimut solar en grados
    """

    # Ángulo de azimut solar

    cos_az = (math.sin(math.radians(decl)) - math.sin(math.radians(alt)) * math.sin(math.radians(latitud))) / (
        math.cos(math.radians(alt)) * math.cos(math.radians(latitud))
    )

    az = math.degrees(math.acos(cos_az))

    if hra > 0:

        az = 360 - az

    return az


# Tripod assembly file


tripod_assembly = "modbuspython/assets/tripod_assembly.glb"
