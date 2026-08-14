"""Shared utilities for Box3D binding generator modules."""

import re
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import yaml


class FieldClassification(Enum):
    """Classification of a struct field for code generation purposes."""
    SCALAR = auto()
    ENUM = auto()
    MATH = auto()
    ID = auto()
    NESTED_STRUCT = auto()
    ARRAY = auto()
    SKIP_ARRAY = auto()
    POINTER = auto()
    UNKNOWN = auto()


def to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    result = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.lower()


def to_godot_name(b3_name: str) -> str:
    """Convert b3Name_Action to snake_case (strips b3 prefix)."""
    name = b3_name
    if name.startswith("b3"):
        name = name[2:]
    return to_snake_case(name)


def to_godot_class_name(b3_name: str) -> str:
    """Convert b3StructName to Box3DStructName."""
    name = b3_name
    if name.startswith("b3"):
        name = name[2:]
    return f"Box3D{name}"


def load_type_map(root: str) -> dict:
    """Load type_map.yaml from project root."""
    path = Path(root) / "tools" / "generator" / "type_map.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def classify_field(
    field,
    type_map: dict,
    all_struct_names: set,
    skip_structs: set,
) -> FieldClassification:
    """Classify a struct field into a conversion category."""
    from parser import is_scalar_type

    t = field.type

    if field.pointer or "*" in t:
        return FieldClassification.POINTER

    if field.array_size is not None:
        if is_scalar_type(t):
            return FieldClassification.ARRAY
        return FieldClassification.SKIP_ARRAY

    if is_scalar_type(t):
        return FieldClassification.SCALAR

    if t in type_map.get("enums", []):
        return FieldClassification.ENUM

    if t in type_map.get("math_types", {}):
        return FieldClassification.MATH

    if t in type_map.get("id_types", {}):
        return FieldClassification.ID

    if t in all_struct_names:
        if t in skip_structs:
            return FieldClassification.POINTER
        return FieldClassification.NESTED_STRUCT

    return FieldClassification.UNKNOWN


def compute_struct_dependencies(structs: list) -> dict[str, set[str]]:
    """Compute dependency graph: struct -> set of structs it depends on."""
    struct_names = {s.name for s in structs}
    deps = {}
    for s in structs:
        deps[s.name] = set()
        for f in s.fields:
            if f.type in struct_names:
                deps[s.name].add(f.type)
    return deps


def topological_sort(structs: list, deps: dict[str, set[str]]) -> list:
    """Sort structs so dependencies come first."""
    struct_map = {s.name: s for s in structs}
    visited = set()
    result = []

    def visit(name: str):
        if name in visited:
            return
        visited.add(name)
        for dep in deps.get(name, set()):
            if dep in struct_map:
                visit(dep)
        if name in struct_map:
            result.append(struct_map[name])

    for s in structs:
        visit(s.name)

    return result


def enum_value_to_godot_name(val_name: str) -> str:
    """Convert b3_enumValue to SCREAMING_SNAKE_CASE (strip b3_ prefix)."""
    name = val_name
    if name.startswith("b3_"):
        name = name[3:]
    return to_snake_case(name).upper()


def enum_value_to_hint_name(val_name: str) -> str:
    """Convert b3_enumValue to snake_case (strip b3_ prefix) for PROPERTY_HINT_ENUM."""
    name = val_name
    if name.startswith("b3_"):
        name = name[3:]
    return to_snake_case(name)


def build_enum_info(parsed_enums, skip_enum_names: set) -> tuple[list, dict]:
    """Build enum name list and constant mapping from parsed enums.

    Returns (enum_names, enum_constants) where:
    - enum_names: list of str (enum type names)
    - enum_constants: {enum_name: [(godot_const_name, b3_val_name), ...]}
      e.g. {b3BodyType: [("STATIC_BODY", "b3_staticBody"), ...]}

    Skips sentinel values ending in 'Count'.
    """
    enum_names = []
    enum_constants = {}

    for e in parsed_enums:
        if e.name in skip_enum_names:
            continue
        enum_names.append(e.name)
        constants = []
        for v in e.values:
            # Skip sentinel values (e.g., b3_bodyTypeCount)
            if v.name.endswith("Count"):
                continue
            godot_name = enum_value_to_godot_name(v.name)
            constants.append((godot_name, v.name))
        enum_constants[e.name] = constants

    return enum_names, enum_constants


# --- Shared type-checking helpers ---

def data_class_filename(struct_name: str) -> str:
    """Convert a struct name to the filename stem used by both docs and code gen.

    Strips b3 prefix then converts to snake_case.
    e.g. "b3Transformation" -> "transformation"
    """
    name = struct_name[2:] if struct_name.startswith("b3") else struct_name
    return to_snake_case(name)


def collect_convertible_fields(
    struct,
    type_map: dict,
    all_struct_names: set,
    skip_structs: set,
) -> list:
    """Return list of (field, classification) tuples for fields that can be exposed.

    Filters out POINTER, SKIP_ARRAY, and UNKNOWN classifications.
    """
    convertible = []
    for field in struct.fields:
        cls = classify_field(field, type_map, all_struct_names, skip_structs)
        if cls not in (FieldClassification.POINTER, FieldClassification.SKIP_ARRAY, FieldClassification.UNKNOWN):
            convertible.append((field, cls))
    return convertible


def _resolve_field_type(field, classification: str, type_map: dict) -> dict:
    """Resolve a classified field to its type representations for all output formats.

    Returns a dict with keys:
      - xml:    Godot class reference XML type string (e.g. "RID", "PackedFloat32Array")
      - variant: Variant::TYPE constant for _bind_methods (e.g. "Variant::INT")
      - cpp:    C++ type for method declarations (e.g. "int64_t", "PackedFloat32Array")
    """
    if classification == FieldClassification.SCALAR:
        t = field.type
        if t == "bool":
            return {"xml": "bool", "variant": "Variant::BOOL", "cpp": "bool"}
        if t == "float":
            return {"xml": "float", "variant": "Variant::FLOAT", "cpp": "float"}
        return {"xml": "int", "variant": "Variant::INT", "cpp": "int"}

    if classification == FieldClassification.ENUM:
        return {"xml": "int", "variant": "Variant::INT", "cpp": field.type}

    if classification == FieldClassification.MATH:
        info = type_map["math_types"][field.type]
        gt = info["godot"]
        variant_map = {
            "Vector3": "Variant::VECTOR3",
            "Quaternion": "Variant::QUATERNION",
            "Transform3D": "Variant::TRANSFORM3D",
            "AABB": "Variant::AABB",
            "Basis": "Variant::BASIS",
            "Plane": "Variant::PLANE",
        }
        return {
            "xml": gt,
            "variant": variant_map.get(gt, "Variant::NIL"),
            "cpp": gt,
        }

    if classification == FieldClassification.ID:
        info = type_map["id_types"][field.type]
        gt = info["godot"]
        if gt == "RID":
            return {"xml": "RID", "variant": "Variant::INT", "cpp": "int64_t"}
        if gt.startswith("Packed"):
            return {"xml": gt, "variant": "Variant::PACKED_INT32_ARRAY", "cpp": gt}
        return {"xml": "int", "variant": "Variant::INT", "cpp": "int"}

    if classification == FieldClassification.NESTED_STRUCT:
        cls_name = to_godot_class_name(field.type)
        return {
            "xml": cls_name,
            "variant": f'Variant::OBJECT, "{cls_name}"',
            "cpp": f"Ref<{cls_name}>",
        }

    if classification == FieldClassification.ARRAY:
        base = field.type
        if base == "float":
            return {
                "xml": "PackedFloat32Array",
                "variant": "Variant::PACKED_FLOAT32_ARRAY",
                "cpp": "PackedFloat32Array",
            }
        return {
            "xml": "PackedInt32Array",
            "variant": "Variant::PACKED_INT32_ARRAY",
            "cpp": "PackedInt32Array",
        }

    return {"xml": "Variant", "variant": "Variant::NIL", "cpp": "Variant"}


def is_string_type(param) -> bool:
    """Check if a parameter is a C string (const char*)."""
    return param.type == "char" and param.pointer


def is_data_class_type(b3_type: str, type_map: dict) -> bool:
    """Check if a b3 struct type should be represented as a data class."""
    return True


def to_godot_param_name(b3_name: str, idx: int) -> str:
    """Convert a b3 parameter name to a Godot parameter name."""
    return f"p_{to_snake_case(b3_name)}"
