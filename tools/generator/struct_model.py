"""Data class field modeling for Box3D structs.

Decides how each struct field maps to Godot (scalar/enum/math/id/nested/array/
pointer/unknown) and resolves a classified field to concrete Godot types for the
C++ declarations, Variant bindings, and XML docs.
"""

from enum import Enum, auto


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


def resolve_field_type(field, classification: str, type_map: dict) -> dict:
    """Resolve a classified field to its type representations for all output formats.

    Returns a dict with keys:
      - xml:    Godot class reference XML type string (e.g. "RID", "PackedFloat32Array")
      - variant: Variant::TYPE constant for _bind_methods (e.g. "Variant::INT")
      - cpp:    C++ type for method declarations (e.g. "int64_t", "PackedFloat32Array")
    """
    from naming import to_godot_class_name

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