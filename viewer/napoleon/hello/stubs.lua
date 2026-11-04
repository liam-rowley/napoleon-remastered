-- purpose: the J31 hello-world's stubbed engine: one fixture (the data model's source) and one engine call
-- usage: loaded by viewer/napoleon/hello/hello.rml (<script src>) in the review viewer; not run in game
-- when: the viewer spike only; real screens get stubs generated from their captured fixtures (UI_PIPELINE section 2.4)
-- not-a-verb: Lua loaded by an RML document in the viewer, not a command

Fixture = {
	faction = "France",
	treasury = 2550,
	turn = 1,
	armies = {
		{ name = "Armee d'Italie", men = 38000 },
		{ name = "Armee du Rhin", men = 61000 },
		{ name = "Armee d'Egypte", men = 32000 },
		{ name = "Garde Imperiale", men = 12000 },
		{ name = "I Corps (Bernadotte)", men = 17000 },
		{ name = "II Corps (Marmont)", men = 20000 },
		{ name = "III Corps (Davout)", men = 26000 },
		{ name = "IV Corps (Soult)", men = 30000 },
		{ name = "V Corps (Lannes)", men = 18000 },
		{ name = "VI Corps (Ney)", men = 22000 },
		{ name = "VII Corps (Augereau)", men = 15000 },
		{ name = "Reserve Cavalry (Murat)", men = 22000 },
	},
}

-- The one engine call: the stub advances the turn the way the game's end-turn would report it.
Engine = {
	EndTurn = function()
		Fixture.turn = Fixture.turn + 1
		return Fixture.turn
	end,
}
