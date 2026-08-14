#pragma once

#include "../precompiled.hpp"

#include <godot_cpp/classes/object.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/typed_array.hpp>
#include <godot_cpp/variant/variant.hpp>

#include "../bindings/data_classes/data_classes.gen.hpp"

// Static GDExtension class that exposes the full Box3D C API directly to Godot,
// independent of the PhysicsServer3D integration. Shares the same RID space so
// objects created by either layer are accessible from both.
class Box3DAPI : public godot::Object {
	GDCLASS(Box3DAPI, Object)

public:
	static void _bind_methods();
	// Auto-generated method declarations
#include "../bindings/box3d_api_generated.gen.hpp"

	// Hand-written: user data (stored as Variant on RID owner, not passed to Box3D void*)
	static void world_set_user_data(godot::RID p_id, godot::Variant p_data);
	static godot::Variant world_get_user_data(godot::RID p_id);
	static void body_set_user_data(godot::RID p_id, godot::Variant p_data);
	static godot::Variant body_get_user_data(godot::RID p_id);
	static void joint_set_user_data(godot::RID p_id, godot::Variant p_data);
	static godot::Variant joint_get_user_data(godot::RID p_id);

	// Hand-written: output scalar pointers → Dictionary
	static godot::Dictionary joint_get_constraint_tuning(godot::RID p_id);
	static godot::Dictionary get_milliseconds_and_reset();

	// Hand-written: INOUT array (b3SolvePlanes modifies planes in place, returns result)
	static godot::Ref<Box3DPlaneSolverResult> solve_planes(godot::Vector3 p_target_delta, godot::Array r_planes);

private:
	Box3DAPI();
};

// Forward declaration for generated registration
void bind_generated_methods();
