#pragma once

#include "../precompiled.hpp"

#include <godot_cpp/classes/object.hpp>

// Static GDExtension class that exposes the full Box3D C API directly to Godot,
// independent of the PhysicsServer3D integration. Shares the same RID space so
// objects created by either layer are accessible from both.
class Box3DAPI : public godot::Object {
	GDCLASS(Box3DAPI, Object)

public:
	static void _bind_methods();

private:
	Box3DAPI();
};
