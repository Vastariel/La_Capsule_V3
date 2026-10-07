extends SceneTree
## Génère le maillage de la navball dans res://Assets/Navball/navball_mesh.res.
## À relancer seulement si on veut changer la résolution de la sphère :
##   godot --headless --path godot_ui -s res://tools/build_ball_mesh.gd
##
## Sphère UV équirectangulaire.
## u = 0.5 + cap/360  (Nord au centre de la texture)
## v = 0.5 - tangage/180  (haut de la texture = +90°)
## La position du sommet est la direction "ciel" avec z inversé (vue extérieure).

const LON := 96
const LAT := 48
const OUTPUT := "res://Assets/Navball/navball_mesh.res"


func _initialize() -> void:
	var err := ResourceSaver.save(_make_ball_mesh(), OUTPUT)
	print("%s : %s" % [OUTPUT, error_string(err)])
	quit()


func _make_ball_mesh() -> ArrayMesh:
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()

	for j in range(LAT + 1):
		var v := float(j) / LAT
		var p := (0.5 - v) * PI
		for i in range(LON + 1):
			var u := float(i) / LON
			var h := (u - 0.5) * TAU
			var pos := Vector3(sin(h) * cos(p), sin(p), cos(h) * cos(p))
			verts.push_back(pos)
			norms.push_back(pos)
			uvs.push_back(Vector2(u, v))

	for j in range(LAT):
		for i in range(LON):
			var a := j * (LON + 1) + i
			var b := a + 1
			var c := a + LON + 1
			var d := c + 1
			idx.push_back(a)
			idx.push_back(b)
			idx.push_back(c)
			idx.push_back(b)
			idx.push_back(d)
			idx.push_back(c)

	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = idx

	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
