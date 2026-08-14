#include "box3d_api.hpp"
#include "box3d_api_helpers.hpp"

#include "../objects/box3d_body_impl_3d.hpp"
#include "../joints/box3d_joint_impl_3d.hpp"
#include "../spaces/box3d_space_3d.hpp"

Box3DAPI::Box3DAPI() {}

void Box3DAPI::_bind_methods() {
	bind_generated_methods();

	ClassDB::bind_static_method("Box3DAPI", D_METHOD("world_set_user_data", "id", "data"), &Box3DAPI::world_set_user_data);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("world_get_user_data", "id"), &Box3DAPI::world_get_user_data);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("body_set_user_data", "id", "data"), &Box3DAPI::body_set_user_data);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("body_get_user_data", "id"), &Box3DAPI::body_get_user_data);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("joint_set_user_data", "id", "data"), &Box3DAPI::joint_set_user_data);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("joint_get_user_data", "id"), &Box3DAPI::joint_get_user_data);

	ClassDB::bind_static_method("Box3DAPI", D_METHOD("joint_get_constraint_tuning", "id"), &Box3DAPI::joint_get_constraint_tuning);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("get_milliseconds_and_reset"), &Box3DAPI::get_milliseconds_and_reset);
	ClassDB::bind_static_method("Box3DAPI", D_METHOD("solve_planes", "target_delta", "planes"), &Box3DAPI::solve_planes);
}

void Box3DAPI::world_set_user_data(RID p_id, Variant p_data) {
	Box3DSpace3D* obj = api_get_space(p_id);
	ERR_FAIL_NULL(obj);
	obj->set_user_data(p_data);
}

Variant Box3DAPI::world_get_user_data(RID p_id) {
	Box3DSpace3D* obj = api_get_space(p_id);
	ERR_FAIL_NULL_V(obj, Variant());
	return obj->get_user_data();
}

void Box3DAPI::body_set_user_data(RID p_id, Variant p_data) {
	Box3DBodyImpl3D* obj = api_get_body(p_id);
	ERR_FAIL_NULL(obj);
	obj->set_user_data(p_data);
}

Variant Box3DAPI::body_get_user_data(RID p_id) {
	Box3DBodyImpl3D* obj = api_get_body(p_id);
	ERR_FAIL_NULL_V(obj, Variant());
	return obj->get_user_data();
}

void Box3DAPI::joint_set_user_data(RID p_id, Variant p_data) {
	Box3DJointImpl3D* obj = api_get_joint(p_id);
	ERR_FAIL_NULL(obj);
	obj->set_user_data(p_data);
}

Variant Box3DAPI::joint_get_user_data(RID p_id) {
	Box3DJointImpl3D* obj = api_get_joint(p_id);
	ERR_FAIL_NULL_V(obj, Variant());
	return obj->get_user_data();
}

Dictionary Box3DAPI::joint_get_constraint_tuning(RID p_id) {
	Box3DJointImpl3D* obj = api_get_joint(p_id);
	ERR_FAIL_NULL_V(obj, Dictionary());
	float hertz = 0, damping = 0;
	b3Joint_GetConstraintTuning(obj->get_joint_id(), &hertz, &damping);
	Dictionary d;
	d["hertz"] = hertz;
	d["damping_ratio"] = damping;
	return d;
}

Dictionary Box3DAPI::get_milliseconds_and_reset() {
	uint64_t ticks = 0;
	float ms = b3GetMillisecondsAndReset(&ticks);
	Dictionary d;
	d["milliseconds"] = ms;
	d["ticks"] = (int64_t)ticks;
	return d;
}
