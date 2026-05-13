from sparql_builder import normalize_lookup


ROLE_TURISTA = "turista"
ROLE_OPERADOR = "operador"
ROLE_ADMIN = "admin"

_ROLE_ALIASES = {
    ROLE_TURISTA: {
        "turista",
        "viajero",
    },
    ROLE_OPERADOR: {
        "operador",
        "prestador",
        "prestador servicio",
        "prestador de servicio",
        "prestador de servicios",
        "agencia",
        "agencia de viajes",
    },
    ROLE_ADMIN: {
        "admin",
        "administrador",
        "administrador general",
    },
}


def normalize_role_name(value: str | None) -> str:
    key = normalize_lookup(value)
    if not key:
        return ROLE_TURISTA
    for normalized, aliases in _ROLE_ALIASES.items():
        if key in aliases:
            return normalized
    return ROLE_TURISTA


def is_admin(value: str | None) -> bool:
    return normalize_role_name(value) == ROLE_ADMIN


def is_operator(value: str | None) -> bool:
    return normalize_role_name(value) == ROLE_OPERADOR


def is_operator_or_admin(value: str | None) -> bool:
    normalized = normalize_role_name(value)
    return normalized in {ROLE_OPERADOR, ROLE_ADMIN}
