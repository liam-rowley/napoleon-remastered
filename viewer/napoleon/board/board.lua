-- purpose: the component board's view code: the data model for the swatches and the faction picker, and the click handlers that make the live components work
-- usage: loaded by viewer/napoleon/board/board.rml after board_data.lua in the review viewer; handlers are called from onclick attributes
-- when: part of the J34 component board; no engine calls and no game data (the faction tint is body classes from uikit/napoleon/dist/factions_synthetic.rcss)
-- not-a-verb: Lua loaded by an RML document in the viewer, not a command

Board = Board or {}

local function note(f)
	if f.adjusted then
		return "The fill was moved 2 percent at a time until the text reached 4.5 (the on-colour fix)."
	end
	return ""
end

if Board.model == nil then
	local factions = {}
	for i, f in ipairs(BoardData.factions) do
		factions[i] = { id = f.id, label = f.label }
	end
	local first = BoardData.factions[1]
	Board.model = rmlui.contexts["main"]:OpenDataModel("board", {
		swatches = BoardData.swatches,
		pairs = BoardData.pairs,
		factions = factions,
		cur = first.id,
		cur_label = first.label,
		cur_fac = first.fac,
		cur_on = first.on,
		cur_ratio = first.ratio,
		cur_note = note(first),
	})
end

-- Select one of a group of siblings (a tab or a row); a disabled sibling keeps its look.
local function select_one(element)
	for _, n in ipairs(element.parent_node.child_nodes) do
		n:SetClass("is-selected", false)
	end
	element:SetClass("is-selected", true)
end

function Board.Tab(element)
	select_one(element)
end

function Board.Row(element)
	select_one(element)
end

function Board.Toggle(element)
	element:SetClass("is-selected", not element:IsClassSet("is-selected"))
end

function Board.Check(element)
	element:SetClass("is-checked", not element:IsClassSet("is-checked"))
end

function Board.Tip(element, show)
	element.owner_document:GetElementById("tip"):SetClass("is-shown", show)
end

-- The faction route: a class on the document body picks the record (body.fac-<id> sets --fac, --on-fac, --fac-hover, --fac-pressed).
function Board.Faction(element)
	local body = element.owner_document
	for _, f in ipairs(BoardData.factions) do
		body:SetClass("fac-" .. f.id, f.id == element.id)
		if f.id == element.id then
			Board.model.cur = f.id
			Board.model.cur_label = f.label
			Board.model.cur_fac = f.fac
			Board.model.cur_on = f.on
			Board.model.cur_ratio = f.ratio
			Board.model.cur_note = note(f)
		end
	end
end
