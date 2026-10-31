-- purpose: the J31 hello-world's view code: opens the "hello" data model from the fixture and handles the End turn click
-- usage: loaded by viewer/napoleon/hello/hello.rml (<script src>, after stubs.lua) in the review viewer
-- when: the viewer spike only; shows layout, text, input and Lua running together (jobs/J31/brief.md)
-- not-a-verb: Lua loaded by an RML document in the viewer, not a command

Hello = Hello or {}

if Hello.model == nil then
	local armies = {}
	for i, a in ipairs(Fixture.armies) do
		armies[i] = { name = a.name, men = a.men }
	end
	Hello.model = rmlui.contexts["main"]:OpenDataModel("hello", {
		faction = Fixture.faction,
		treasury = Fixture.treasury,
		turn = Fixture.turn,
		-- float32 Lua: 816 (a double Lua gives 815)
		tax = math.floor(Fixture.treasury * 0.319999992),
		armies = armies,
		last_event = "",
	})
end

function Hello.EndTurn()
	local turn = Engine.EndTurn()
	Hello.model.turn = turn
	Hello.model.last_event = "Engine.EndTurn() returned " .. turn
end
