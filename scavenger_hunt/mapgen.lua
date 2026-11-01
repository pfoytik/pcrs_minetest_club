-- Runs in the map generator's own thread (the "mapgen environment").
-- Each time a new chunk of land (80x80x80 nodes) is generated, maybe hide
-- Hunt Stars in it - on the surface, under water, or in caves - then tell
-- the main game where they went.

local STAR = "scavenger_hunt:star"
local function setting(name, default)
	return tonumber(core.settings:get("scavenger_hunt." .. name)) or default
end
local CHANCE = setting("chance", 0.5)
local PER_AREA = math.max(1, math.min(50, setting("per_area", 1)))
local UNDERWATER = math.max(0, math.min(1, setting("underwater", 0.5)))
local CAVES_PER_AREA = math.max(0, math.min(50, setting("caves_per_area", 1)))
local CAVE_MIN_Y = setting("cave_min_y", -80)
local ENABLED = core.settings:get_bool("scavenger_hunt.mapgen", true)

local ATTEMPTS = 8         -- random spots to try for each star
local MAX_WATER_DEPTH = 12 -- deeper than this is too far to swim down
local SUNLIGHT = 15        -- light level of a spot open to the sky

local function def_of(node)
	return core.registered_nodes[node.name]
end

local function is_liquid(def)
	return def and (def.liquidtype or "none") ~= "none"
end

local function is_solid_ground(node)
	local def = def_of(node)
	-- solid, not water, and not treetops (no stars stuck up in the canopy)
	return def and def.walkable and not is_liquid(def)
		and not (def.groups and (def.groups.leaves or def.groups.tree))
end

local function is_open_space(node)
	if node.name == "air" then
		return true
	end
	-- grass tufts, snow layers, flowers: things a star can replace
	local def = def_of(node)
	return def and def.buildable_to and not is_liquid(def)
end

local function sunlit(node)
	return node.param1 % 16 == SUNLIGHT -- daylight part of the light value
end

local function place(pos, placed)
	core.set_node(pos, {name = STAR})
	table.insert(placed, pos)
end

-- One star on land in the open, or on the floor of shallow open water.
local function try_surface(pr, heightmap, minp, maxp, placed)
	local sidelen = maxp.x - minp.x + 1
	for _ = 1, ATTEMPTS do
		local x = pr:next(minp.x, maxp.x)
		local z = pr:next(minp.z, maxp.z)
		-- heightmap = first solid node from the top of THIS chunk down
		local y = heightmap[(z - minp.z) * sidelen + (x - minp.x) + 1]
		if y and y >= minp.y and y + 1 <= maxp.y
				and is_solid_ground(core.get_node({x = x, y = y, z = z})) then
			local pos = {x = x, y = y + 1, z = z}
			local above = core.get_node(pos)
			if is_open_space(above) then
				-- sunlight tells real open sky from a cave cut by the chunk top
				if sunlit(above) then
					place(pos, placed)
					return
				end
			elseif is_liquid(def_of(above)) and UNDERWATER > 0
					and pr:next(1, 1000) <= UNDERWATER * 1000 then
				-- find the water's surface: must be open sky, not too deep
				local top = pos.y
				while top + 1 <= maxp.y
						and is_liquid(def_of(core.get_node({x = x, y = top + 1, z = z}))) do
					top = top + 1
				end
				local surface = top + 1 <= maxp.y and core.get_node({x = x, y = top + 1, z = z})
				if surface and surface.name == "air" and sunlit(surface)
						and top - y <= MAX_WATER_DEPTH then
					place(pos, placed)
					return
				end
			end
		end
	end
end

-- One star on a cave floor: rock above, solid floor, room to stand, dark.
-- (The rock-ceiling check keeps stars off forest floors, which are dark too.)
local function try_cave(pr, minp, maxp, placed)
	local bottom = math.max(minp.y + 1, CAVE_MIN_Y)
	if maxp.y - 1 < bottom then
		return
	end
	for _ = 1, ATTEMPTS do
		local x = pr:next(minp.x, maxp.x)
		local z = pr:next(minp.z, maxp.z)
		local spots = {}
		local under_rock = false -- is the nearest non-air node above us rock?
		for y = maxp.y, bottom, -1 do
			local pos = {x = x, y = y, z = z}
			local here = core.get_node(pos)
			if here.name ~= "air" then
				under_rock = is_solid_ground(here)
			elseif under_rock and y < maxp.y and not sunlit(here)
					and core.get_node({x = x, y = y + 1, z = z}).name == "air"
					and is_solid_ground(core.get_node({x = x, y = y - 1, z = z})) then
				table.insert(spots, pos)
			end
		end
		if #spots > 0 then
			place(spots[pr:next(1, #spots)], placed)
			return
		end
	end
end

core.register_on_generated(function(vmanip, minp, maxp, blockseed)
	if not ENABLED then
		return
	end
	-- Same world + same chunk = same result, so stars are reproducible
	local pr = PcgRandom(blockseed + 7919)
	if pr:next(1, 1000) > CHANCE * 1000 then
		return
	end
	local heightmap = core.get_mapgen_object("heightmap")
	if not heightmap then
		return
	end

	local placed = {}
	for _ = 1, PER_AREA do
		try_surface(pr, heightmap, minp, maxp, placed)
	end
	for _ = 1, CAVES_PER_AREA do
		try_cave(pr, minp, maxp, placed)
	end

	if #placed > 0 then
		vmanip:calc_lighting() -- so the stars glow straight away
		core.save_gen_notify("scavenger_hunt:placed", placed)
	end
end)
