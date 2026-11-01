-- Scavenger Hunt: glowing Hunt Stars hidden across the world.
--
-- Stars appear by themselves as new land is generated (see mapgen.lua), so
-- the area around spawn runs out and students have to explore to find more.
-- Teachers can also scatter stars with /hunt_scatter, or place them by hand.
--
-- Only stars this mod placed (or a teacher placed) score points, and scores
-- are kept by the mod, not read from inventories, so creative mode can't be
-- used to cheat.

scavenger_hunt = {}

local S = core.get_translator("scavenger_hunt")
local STAR = "scavenger_hunt:star"
local TOKEN = "scavenger_hunt:star_token"
local TEACHER_PRIV = "server"
local GOLD = "#FFD700"
local storage = core.get_mod_storage()

--------------------------------------------------------------------------
-- Saved data: which positions hold real hunt stars, and everyone's score
--------------------------------------------------------------------------

local stars = core.deserialize(storage:get_string("stars")) or {}
local star_count = 0
for _ in pairs(stars) do
	star_count = star_count + 1
end

local function save_stars()
	storage:set_string("stars", core.serialize(stars))
end

local function add_star(pos)
	local h = core.hash_node_position(vector.round(pos))
	if not stars[h] then
		stars[h] = true
		star_count = star_count + 1
		save_stars()
	end
end

local function take_star(pos)
	local h = core.hash_node_position(pos)
	if stars[h] then
		stars[h] = nil
		star_count = star_count - 1
		save_stars()
		return true
	end
	return false
end

function scavenger_hunt.get_score(name)
	return storage:get_int("score:" .. name)
end

local function add_score(name)
	local n = scavenger_hunt.get_score(name) + 1
	storage:set_int("score:" .. name, n)
	storage:set_int("total_found", storage:get_int("total_found") + 1)
	return n
end

-- All scores, highest first: { {name=, score=}, ... }
function scavenger_hunt.get_scores()
	local list = {}
	for key in pairs(storage:to_table().fields) do
		local name = key:match("^score:(.+)$")
		if name then
			table.insert(list, {name = name, score = storage:get_int(key)})
		end
	end
	table.sort(list, function(a, b)
		if a.score ~= b.score then
			return a.score > b.score
		end
		return a.name < b.name
	end)
	return list
end

function scavenger_hunt.remaining()
	return star_count
end

scavenger_hunt.add_star = add_star

--------------------------------------------------------------------------
-- Effects
--------------------------------------------------------------------------

-- A slow column of sparkles rising from each star, so it can be spotted over
-- hills and through trees. Runs only near players (active blocks).
local function beacon(pos)
	core.add_particlespawner({
		amount = 14,
		time = 3,
		minpos = vector.offset(pos, -0.3, -0.2, -0.3),
		maxpos = vector.offset(pos, 0.3, 0.3, 0.3),
		minvel = {x = -0.15, y = 2.5, z = -0.15},
		maxvel = {x = 0.15, y = 4.5, z = 0.15},
		minexptime = 2.5,
		maxexptime = 3.5,
		minsize = 2,
		maxsize = 4,
		glow = 14,
		texture = "scavenger_hunt_sparkle.png",
	})
end

-- A burst of sparkles when a star is collected
local function burst(pos)
	core.add_particlespawner({
		amount = 50,
		time = 0.2,
		minpos = vector.offset(pos, -0.2, -0.2, -0.2),
		maxpos = vector.offset(pos, 0.2, 0.2, 0.2),
		minvel = {x = -4, y = 1, z = -4},
		maxvel = {x = 4, y = 7, z = 4},
		minacc = {x = 0, y = -9, z = 0},
		maxacc = {x = 0, y = -9, z = 0},
		minexptime = 0.8,
		maxexptime = 1.6,
		minsize = 2,
		maxsize = 5,
		glow = 14,
		texture = "scavenger_hunt_sparkle.png",
	})
end

--------------------------------------------------------------------------
-- Collecting a star
--------------------------------------------------------------------------

local function collect(pos, digger)
	if not (digger and digger:is_player()) then
		return false
	end
	local name = digger:get_player_name()
	core.remove_node(pos)
	burst(pos)

	if not take_star(pos) then
		-- Not one of ours (e.g. copied with middle-click in creative): no points
		core.chat_send_player(name, S("That star was a fake - no points!"))
		return true
	end

	local score = add_score(name)
	local inv = digger:get_inventory()
	local leftover = inv:add_item("main", ItemStack(TOKEN))
	if not leftover:is_empty() then
		core.add_item(pos, leftover)
	end

	core.log("action", name .. " found a hunt star at " ..
		core.pos_to_string(pos) .. ", total " .. score)
	if core.settings:get_bool("scavenger_hunt.announce", true) then
		core.chat_send_all(core.colorize(GOLD,
			S("@1 found a Hunt Star! (@2 total)", name, score)))
	else
		core.chat_send_player(name, core.colorize(GOLD,
			S("You found a Hunt Star! (@1 total)", score)))
	end
	return true
end

--------------------------------------------------------------------------
-- Nodes and items
--------------------------------------------------------------------------

core.register_node(STAR, {
	description = S("Hunt Star"),
	drawtype = "plantlike",
	tiles = {{
		name = "scavenger_hunt_star_anim.png",
		animation = {type = "vertical_frames", aspect_w = 32, aspect_h = 32, length = 1.6},
	}},
	inventory_image = "scavenger_hunt_star.png",
	wield_image = "scavenger_hunt_star.png",
	visual_scale = 1.3,
	paramtype = "light",
	sunlight_propagates = true,
	light_source = core.LIGHT_MAX, -- as bright as a block can be
	walkable = false,
	selection_box = {type = "fixed", fixed = {-0.4, -0.5, -0.4, 0.4, 0.5, 0.4}},
	groups = {dig_immediate = 3, not_in_creative_inventory = 1},
	drop = "",
	on_blast = function() end, -- TNT can't destroy (or steal) stars

	-- Only teachers can place stars by hand; those count like hidden ones
	on_place = function(itemstack, placer, pointed_thing)
		if not (placer and core.check_player_privs(placer, TEACHER_PRIV)) then
			if placer and placer:is_player() then
				core.chat_send_player(placer:get_player_name(),
					S("Only teachers can hide Hunt Stars."))
			end
			return itemstack
		end
		return core.item_place(itemstack, placer, pointed_thing)
	end,
	after_place_node = function(pos)
		add_star(pos)
	end,

	on_dig = function(pos, node, digger)
		return collect(pos, digger)
	end,
})

-- What students keep after collecting a star
core.register_craftitem(TOKEN, {
	description = S("Collected Hunt Star") .. "\n" ..
		core.colorize("#AAAAAA", S("Proof of a successful hunt")),
	inventory_image = "scavenger_hunt_star.png",
	groups = {not_in_creative_inventory = 1},
	stack_max = 999,
})

core.register_abm({
	label = "Hunt Star sparkle beacon",
	nodenames = {STAR},
	interval = 3,
	chance = 1,
	catch_up = false,
	action = beacon,
})

--------------------------------------------------------------------------
-- Stars hidden by the map generator (mapgen.lua) are reported here
--------------------------------------------------------------------------

-- The "custom" flag must be on too, or the engine silently drops custom ids
core.set_gen_notify({custom = true}, nil, {"scavenger_hunt:placed"})
core.register_mapgen_script(core.get_modpath("scavenger_hunt") .. "/mapgen.lua")

core.register_on_generated(function()
	local notify = core.get_mapgen_object("gennotify")
	local placed = notify and notify.custom and notify.custom["scavenger_hunt:placed"]
	for _, pos in ipairs(placed or {}) do
		add_star(pos)
	end
end)

--------------------------------------------------------------------------
-- Scattering stars around a point (for land that already exists)
--------------------------------------------------------------------------

local CAVE_MIN_Y = tonumber(core.settings:get("scavenger_hunt.cave_min_y")) or -80
local SCAN_TOP = 120
local SCAN_BOTTOM = math.min(-40, CAVE_MIN_Y)
local MAX_WATER_DEPTH = 12

local function is_liquid(def)
	return (def.liquidtype or "none") ~= "none"
end

local function is_solid(def)
	return def.walkable and not is_liquid(def)
		and not (def.groups and (def.groups.leaves or def.groups.tree))
end

-- A spot for a star in this column, or nil. mode is "land", "water" or "cave":
--   land:  on the ground in the open
--   water: on the floor of open water at most MAX_WATER_DEPTH deep
--   cave:  on a cave floor with rock above and room to stand
local function find_spot(x, z, mode)
	local spots = {}
	local surface_found, water_top, under_rock = false, nil, false
	for y = SCAN_TOP, SCAN_BOTTOM, -1 do
		local pos = {x = x, y = y, z = z}
		local name = core.get_node(pos).name
		local def = core.registered_nodes[name]
		if name == "ignore" or not def then
			break
		end
		if not surface_found then
			local passable = name == "air" or (def.groups and def.groups.leaves)
				or (def.buildable_to and not is_liquid(def))
			if is_liquid(def) then
				water_top = water_top or y
			elseif not passable then
				-- reached the ground (or the bottom of the water)
				surface_found = true
				local above = {x = x, y = y + 1, z = z}
				if not is_solid(def) or core.get_node(above).name == STAR then
					if mode ~= "cave" then
						return nil
					end
				elseif mode == "land" and not water_top then
					return above
				elseif mode == "water" and water_top then
					return water_top - y <= MAX_WATER_DEPTH and above or nil
				elseif mode ~= "cave" then
					return nil
				end
				under_rock = is_solid(def)
			end
		elseif name ~= "air" then
			under_rock = is_solid(def)
		elseif under_rock and y >= CAVE_MIN_Y
				and core.get_node({x = x, y = y + 1, z = z}).name == "air"
				and is_solid(core.registered_nodes[core.get_node({x = x, y = y - 1, z = z}).name] or {})
				and (core.get_natural_light(pos, 0.5) or 0) < 15 then
			table.insert(spots, pos)
		end
	end
	return #spots > 0 and spots[math.random(#spots)] or nil
end

-- Hide up to `count` stars at random spots within `radius` of `center`.
-- `mode` is "land" (default), "water" or "cave". Missing land is generated
-- first. `done(placed)` is called at the end.
function scavenger_hunt.scatter(center, count, radius, done, mode)
	mode = mode or "land"
	-- Water and caves aren't in every column, so try more spots for those
	local tries = mode == "land" and count or count * 10
	local placed, pending = 0, tries
	local function finish_one()
		pending = pending - 1
		if pending == 0 and done then
			done(placed)
		end
	end
	for _ = 1, tries do
		local x = math.floor(center.x + math.random(-radius, radius))
		local z = math.floor(center.z + math.random(-radius, radius))
		core.emerge_area({x = x, y = SCAN_BOTTOM, z = z}, {x = x, y = SCAN_TOP, z = z},
			function(_, _, calls_remaining)
				if calls_remaining > 0 then
					return
				end
				local pos = placed < count and find_spot(x, z, mode)
				if pos then
					core.set_node(pos, {name = STAR})
					add_star(pos)
					placed = placed + 1
				end
				finish_one()
			end)
	end
end

-- Set everyone's score back to 0 (hidden stars stay where they are).
function scavenger_hunt.reset_scores()
	for key in pairs(storage:to_table().fields) do
		if key:match("^score:") then
			storage:set_string(key, "")
		end
	end
	storage:set_string("total_found", "")
end

function scavenger_hunt.total_found()
	return storage:get_int("total_found")
end

-- Remove every hunt star still in the world. Returns how many were removed.
function scavenger_hunt.clear_all()
	local removed = 0
	for h in pairs(stars) do
		local pos = core.get_position_from_hash(h)
		core.load_area(pos)
		if core.get_node(pos).name == STAR then
			core.remove_node(pos)
			removed = removed + 1
		end
	end
	stars, star_count = {}, 0
	save_stars()
	return removed
end

--------------------------------------------------------------------------
-- Chat commands
--------------------------------------------------------------------------

core.register_chatcommand("hunt", {
	description = S("Show the Hunt Star leaderboard"),
	func = function(name)
		local scores = scavenger_hunt.get_scores()
		local lines = {core.colorize(GOLD, S("Hunt Star leaderboard"))}
		if #scores == 0 then
			table.insert(lines, S("No stars found yet - go explore!"))
		end
		for i = 1, math.min(10, #scores) do
			table.insert(lines, ("%d. %s - %d"):format(i, scores[i].name, scores[i].score))
		end
		table.insert(lines, S("You have found @1.", scavenger_hunt.get_score(name)))
		return true, table.concat(lines, "\n")
	end,
})

core.register_chatcommand("hunt_scatter", {
	params = S("<count> [radius] [land|water|cave]"),
	description = S("Hide Hunt Stars at random spots around you (default radius 200, on land)"),
	privs = {[TEACHER_PRIV] = true},
	func = function(name, param)
		local count, radius, mode = param:match("^(%d+)%s*(%d*)%s*(%a*)$")
		count, radius = tonumber(count), tonumber(radius) or 200
		mode = (mode or "") == "" and "land" or mode
		if not count or count < 1 or count > 200 or radius < 5 or radius > 2000
				or not (mode == "land" or mode == "water" or mode == "cave") then
			return false, S("Usage: /hunt_scatter <count 1-200> [radius 5-2000] [land|water|cave]")
		end
		local player = core.get_player_by_name(name)
		if not player then
			return false, S("You must be in the game to use this.")
		end
		scavenger_hunt.scatter(player:get_pos(), count, radius, function(placed)
			core.chat_send_player(name, S("Hid @1 of @2 stars (@3). @4 hidden in total.",
				placed, count, mode, star_count))
		end, mode)
		return true, S("Hiding stars... (new land may take a moment to generate)")
	end,
})

core.register_chatcommand("hunt_status", {
	description = S("Teacher: how many stars are hidden and found"),
	privs = {[TEACHER_PRIV] = true},
	func = function()
		return true, S("Hidden and not yet found: @1. Found so far: @2. Players scoring: @3.",
			star_count, storage:get_int("total_found"), #scavenger_hunt.get_scores())
	end,
})

core.register_chatcommand("hunt_clear", {
	params = "yes",
	description = S("Teacher: remove every hidden star from the world (scores are kept)"),
	privs = {[TEACHER_PRIV] = true},
	func = function(_, param)
		if param ~= "yes" then
			return false, S("This removes all @1 hidden stars. Type /hunt_clear yes to confirm.", star_count)
		end
		return true, S("Removed @1 stars.", scavenger_hunt.clear_all())
	end,
})

core.register_chatcommand("hunt_reset", {
	params = "yes",
	description = S("Teacher: set everyone's score back to 0 (stars stay hidden)"),
	privs = {[TEACHER_PRIV] = true},
	func = function(_, param)
		if param ~= "yes" then
			return false, S("This erases all scores. Type /hunt_reset yes to confirm.")
		end
		scavenger_hunt.reset_scores()
		return true, S("All scores reset.")
	end,
})

--------------------------------------------------------------------------
-- Team chests: remember who placed each chest
--------------------------------------------------------------------------
-- Stars stored in a chest count for the team of whoever placed it (see
-- club_scripts/hunt_stats.py), so teammates can share a chest without
-- having to lock it. Locked chests already record their owner.

local chest = core.registered_nodes["default:chest"]
if chest then
	local old_after_place = chest.after_place_node
	core.override_item("default:chest", {
		after_place_node = function(pos, placer, itemstack, pointed_thing)
			if placer and placer:is_player() then
				local name = placer:get_player_name()
				local meta = core.get_meta(pos)
				meta:set_string("placed_by", name)
				meta:set_string("infotext", S("Chest (placed by @1)", name))
			end
			if old_after_place then
				return old_after_place(pos, placer, itemstack, pointed_thing)
			end
		end,
	})
end

-- Remote control from club_scripts/hunt_control.py
dofile(core.get_modpath("scavenger_hunt") .. "/control.lua")
