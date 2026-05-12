from datetime import date, datetime
from decimal import Decimal
import re
import unicodedata
from urllib.parse import unquote

from rdflib import Literal
from rdflib.namespace import XSD


EX = "http://amaturis.org/ontology#"

PREFIXES = """PREFIX ex: <http://amaturis.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

_IRI_RE = re.compile(r"^https?://[^\s<>{}|\\^`\"']+$", re.IGNORECASE)
_LOCAL_ID_RE = re.compile(r"^[A-Za-z0-9_.:%~-]+$")
_CLASS_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def normalize_lookup(value: str | None) -> str:
    text = normalize_text(value).lower()
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()


def literal(value, datatype=None, lang: str | None = None) -> str:
    if datatype is not None:
        return Literal(value, datatype=datatype).n3()
    if lang is not None:
        return Literal(value, lang=lang).n3()
    return Literal(value).n3()


def date_literal(value: date | str) -> str:
    if isinstance(value, date):
        value = value.isoformat()
    return literal(value, datatype=XSD.date)


def datetime_literal(value: datetime | str) -> str:
    if isinstance(value, datetime):
        value = value.isoformat()
    return literal(value, datatype=XSD.dateTime)


def bool_literal(value: bool) -> str:
    return literal(value, datatype=XSD.boolean)


def int_value(value, *, default: int = 0, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def decimal_value(
    value,
    *,
    default: Decimal | int | float = 0,
    minimum: Decimal | int | float | None = None,
    maximum: Decimal | int | float | None = None,
) -> str:
    try:
        number = Decimal(str(value))
    except Exception:
        number = Decimal(str(default))
    if minimum is not None:
        number = max(Decimal(str(minimum)), number)
    if maximum is not None:
        number = min(Decimal(str(maximum)), number)
    return format(number, "f")


def limit_value(value, *, default: int = 50, maximum: int = 300) -> int:
    return int_value(value, default=default, minimum=1, maximum=maximum)


def offset_value(value, *, default: int = 0) -> int:
    return int_value(value, default=default, minimum=0)


def order_by(value: str | None, allowed: dict[str, str], default: str) -> str:
    key = normalize_text(value).lower() or default
    return allowed.get(key, allowed[default])


def local_name(value: str) -> str:
    name = normalize_text(value)
    if not _CLASS_ID_RE.fullmatch(name):
        raise ValueError(f"Nombre RDF invalido: {value}")
    return name


def resource(value: str) -> str:
    text = normalize_text(unquote(str(value)))
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1].strip()
    if text.startswith("ex:"):
        text = text[3:]
    if text.startswith(EX):
        return f"<{_validate_iri(text)}>"
    if _IRI_RE.fullmatch(text):
        return f"<{text}>"
    if _LOCAL_ID_RE.fullmatch(text):
        return f"<{EX}{text}>"
    raise ValueError(f"Identificador RDF invalido: {value}")


def resource_uri(value: str) -> str:
    return resource(value)[1:-1]


def local_resource(local_id: str) -> str:
    text = normalize_text(local_id)
    if not _LOCAL_ID_RE.fullmatch(text):
        raise ValueError(f"Identificador local RDF invalido: {local_id}")
    return f"<{EX}{text}>"


def local_resource_uri(local_id: str) -> str:
    return local_resource(local_id)[1:-1]


def class_resource(class_name: str) -> str:
    return f"ex:{local_name(class_name)}"


def _validate_iri(value: str) -> str:
    if not _IRI_RE.fullmatch(value):
        raise ValueError(f"IRI RDF invalida: {value}")
    return value
