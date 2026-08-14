"""Naming conventions — Box3D C names to Godot names and back.

Holds every rule for deriving Godot identifiers (method names, class names,
parameter names, enum constants, data class filenames) from their Box3D
counterparts.
"""

import re


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


def to_godot_param_name(b3_name: str, idx: int) -> str:
    """Convert a b3 parameter name to a Godot parameter name."""
    return f"p_{to_snake_case(b3_name)}"


def data_class_filename(struct_name: str) -> str:
    """Convert a struct name to the filename stem used by both docs and code gen.

    Strips b3 prefix then converts to snake_case.
    e.g. "b3Transformation" -> "transformation"
    """
    name = struct_name[2:] if struct_name.startswith("b3") else struct_name
    return to_snake_case(name)


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