"""The repairs a frozen candidate may receive without re-reading the source.

A review of one candidate found four ways the model's own output outran what the page
says, and one way two of its outputs contradict each other:

* a team was typed as a post ("专业策划团队" is an organisation arrangement, not a
  Position), and an arrangement inherited "as-is" from a page title that itself says
  "升级" — a page that mixes what stands and what is proposed cannot lend its state to
  a cell that says nothing;
* a duty printed beside a row label was bound to the unit in the other row, and the
  gate answered "which row is this?" instead of proposing the row the layout shows;
* an event's ends were left empty although the sentence names them — the contract's own
  example sentence is the one that failed;
* an UNKNOWN that the candidate later answered kept saying "the page does not explain
  this", so a consumer could find the answer and the refusal at once.

Each function here is a small, testable decision over fields that are already on disk.
None of them reads a model, a page image or the frozen candidate's receipt, and none of
them writes: a repair pass collects the verdicts and a driver applies them, so what
changed and why stays visible next to the record it changed.

**What these functions may decide, and what they must refuse.** A second review ran them
against sentences the card does not contain and found four over-readings, each now a case
in `tests/test_understand_repairs.py`:

* 「尚未确定是否保留甲法人主体」 was read as a certain keep — uncertainty is not a value;
* 「甲公司未合并到乙公司」 produced a merge whose source was 「甲公司未」 — a negated change
  states no ends, and no name may be built out of the negation;
* 「市场营销中心」 against 「区域市场营销中心」 were taken for one end by substring — two
  names are one end only where a registry says the short form names that unit;
* a `to-be` value inherited from 「现状与调整方案对照」 — a heading that prints both what
  stands and what is proposed lends neither.

The rule behind them: accept only an affirmed, evidence-bounded statement or an explicitly
registered name; negation, condition, uncertainty, several subjects, a mixed page and
substring-similar names return "not decided" instead of a value. Refusing too much shows up
downstream as a record that stays open; reading too much goes unnoticed.

**A short name inside one sentence.** `same_end` refuses to fold 「智静」 into 「天水智静」
without a registration, and that stays true: nothing here registers an alias. What a page
can still say is narrower — *in this sentence, on this row, the short name means the box
the row's arrow points at*. `local_end_reference` reads exactly that, cites the sentence,
both boxes and the arrow, and refuses when the row or the page leaves more than one
candidate. The short form and the full name are carried side by side; the binding is not
folded into any name the document holds.

**Scope.** These functions were written against the reviewed sentences of one card and are
not a general semantic method: they are the smallest rules that settle the cases a review
named, plus the refusals above. A card that needs more than "affirmed and bounded" — a
conditional event, a short name with no row of its own, an edge the page never drew — gets
"not decided", not a wider keyword list.
"""
from __future__ import annotations

import hashlib
import re

# A post is someone's position. The names that end in one of these are posts; a name
# that ends in an organisational form is an organisation, whatever type was proposed.
_POST_FORMS = ("经理", "主管", "主任", "专员", "工程师", "总监", "总裁", "董事长", "主席",
               "书记", "科长", "组长", "队长", "负责人", "助理", "秘书", "会计", "出纳",
               "干事", "顾问", "代表", "委员", "部长", "副总", "总工", "岗位")
_ORG_FORMS = ("团队", "小组", "中心", "委员会", "办公室", "项目部", "分公司", "子公司",
              "部门", "集团", "公司", "车间", "班组", "院所", "处室")

# Words a page heading uses to say it is arranging something, not describing what is.
_PLAN_MARKS = ("升级", "调整", "优化", "改革", "方案", "建议", "规划", "改造", "整合")
# Words a page heading uses to say it is talking about what stands today. A heading with
# both sets prints the two side by side ("现状与调整方案对照"), so it lends neither.
_STANDING_MARKS = ("现状", "现有", "当前", "目前", "原有")

_INTEGRATE = re.compile(r"整合([^，。；]+?)[，,]\s*设置为([^，。；]+)")
_MERGE = re.compile(r"([^，。；]{1,12}?)合并到([^，。；]{1,12})")
_KEEPS = re.compile(r"保留[^，。；]{0,6}?法人")
_ABANDONS = re.compile(r"(?:不再|不|未)保留[^，。；]{0,6}?法人")
# A change a sentence denies ("未合并到", "尚未整合") states no ends at all.
_NEGATION = re.compile(r"(?:未|不再|没有|尚未|不曾|不予|不会)")
# A negation attached to the end of a captured subject is part of the denial, not a name.
_TRAILING_NEGATION = re.compile(r"(?:未|不再|没有|尚未|不曾|不予|不会)$")
# A change a sentence puts under a condition ("若甲公司合并到乙公司") is a hypothesis, not an
# event: the card records what the page states, and the page here states a possibility.
_CONDITION = re.compile(r"(?:若|如果|如若|如|一旦|倘若|假如|除非|设若)")
# The same marker at the very start of a captured subject: 「若甲公司」 is not a unit name.
_LEADING_CONDITION = re.compile(r"^(?:若|如果|如若|如|一旦|倘若|假如|除非|设若)")
# Wording that leaves the legal person undecided instead of stating it.
_UNCERTAIN = ("尚未", "是否", "待定", "未确定", "不确定", "待研究", "待确认", "未明确",
              "另议", "拟")
# A parenthetical tail is a note on the name, not the name's form: 总工程师（技术副经理）
# is a post named 总工程师.
_NOTE = re.compile(r"[（(][^（()）]*[）)]$")
# An absence this entry claims about the page itself: either the page is the subject
# ("页面未说明…"), or the page's clause is left dangling and the next clause carries the
# verb ("页面另列…两项表述，未说明…").  A clause with its own subject — 「来源未说明版本
# 效力」 — is about that subject, not about what the page lacks.
_ABSENCE_DIRECT = re.compile(r"页面(?:未说明|未以|没有说明|没有|未)")
_ABSENCE_AFTER_CLAUSE = re.compile(
    r"页面[^。；，]{0,24}，\s*(?:均|都|也|但|却|并|同时)?\s*(?:未说明|没有说明|未)")


def bare_name(name: str | None) -> str:
    """A name with its layout notes and spaces removed, keeping the name's own form."""
    body = re.sub(r"[\s\u3000]+", "", str(name or ""))
    while True:
        shorter = _NOTE.sub("", body)
        if shorter == body:
            return body
        body = shorter


def position_eligible(name: str | None) -> tuple[bool, str]:
    """Whether a name may carry the Position type at all.

    A Chinese post name ends in what the post is called (经理、专员、工程师…). A name that
    ends in an organisational form is a unit even when the page prints it inside a box
    that talks about who will do the work: "在公司层面成立专业策划团队" arranges a team,
    it does not describe a position that already exists.
    """
    body = bare_name(name)
    if not body:
        return False, "没有名字，无法判断是不是岗位"
    if any(body.endswith(form) for form in _POST_FORMS):
        return True, "名称以岗位称谓结尾"
    for form in _ORG_FORMS:
        if body.endswith(form):
            return False, f"名称以组织形态「{form}」结尾，不是岗位"
    return False, "名称既不是岗位称谓、也不是已登记的组织形态；撤掉类型，等映射"


def page_state_inheritable(value: str | None, heading: str | None) -> tuple[bool, str]:
    """Whether a page-level state may be lent to a cell that says nothing.

    A heading that only says "现有组织结构" can: the whole page is the current chart. A
    heading that also says "升级 / 调整 / 优化" mixes what stands with what is proposed,
    so the page cannot tell a silent cell which one it belongs to — and a heading that
    prints both ("现状与调整方案对照") lends neither, not even `to-be`.
    """
    if value not in ("as-is", "to-be"):
        return False, "没有可继承的状态"
    body = str(heading or "")
    marks = [mark for mark in _PLAN_MARKS if mark in body]
    standing = [mark for mark in _STANDING_MARKS if mark in body]
    if marks and standing:
        return False, (f"标题里既有「{'、'.join(standing)}」又有「{'、'.join(marks)}」："
                       f"这一页把现状与调整印在一起，两种状态都不能借")
    if value == "as-is" and marks:
        return False, f"本页标题里有「{'、'.join(marks)}」，这一页在讲调整，不能把现状借给不表态的格子"
    return True, "本页只在说一种状态"


def rebind_holder(holder: str | None, band_holder: str | None, sentence: str = "",
                  layout_ref: str = "") -> dict | None:
    """The holder a row actually has, when the sentence does not name one.

    A row of a page prints the unit on one side and its note on the other; the note's
    holder is the unit in the same row. When the bound holder is the unit in the *other*
    row, the binding is wrong and the layout already says which one is right — that is a
    correction with evidence, not a question for the Owner.
    """
    band = str(band_holder or "").strip()
    if not band:
        return None
    if str(holder or "").strip() == band:
        return None
    flat_sentence = re.sub(r"\s+", "", str(sentence or ""))
    if holder and re.sub(r"\s+", "", str(holder)) in flat_sentence:
        return None  # the sentence names the holder: prose wins over the layout
    if band in flat_sentence:
        return None
    return {"holder": band,
            "why": f"版式同一行：这一格与「{band}」并排（{layout_ref or '同一纵带'}）；"
                   f"原来的持有人「{holder or '空'}」不在这一行"}


def event_ends(statement: str | None) -> dict | None:
    """The units before and after a change, read from the sentence that states it.

    The contract's own example is the one a candidate got wrong: 「整合投资管理中心、市场
    营销中心，设置为市场营销中心」 is one event with two units before the change and one
    after. A merge reads 「甲合并到乙」. Only ends the sentence names are returned, and a
    sentence that hedges states none: 「甲公司未合并到乙公司」 is a denial, not a merge whose
    source is 「甲公司未」, and 「若甲公司合并到乙公司，则另行评估」 is a hypothesis. Both are
    read before any end is taken.
    """
    body = re.sub(r"\s+", "", str(statement or ""))
    for hit in _INTEGRATE.finditer(body):
        if _hedged(body, hit.start()):
            continue
        before = [part for part in re.split(r"[、,，]", hit.group(1)) if part.strip()]
        after = [part.strip() for part in re.split(r"[、,，]", hit.group(2)) if part.strip()]
        if before and after:
            return {"from": before, "to": after}
    for hit in _MERGE.finditer(body):
        # A subject that ends in the negation ("甲公司未合并到乙公司") or opens with a
        # condition ("若甲公司合并到乙公司") is not a unit name.
        subject = hit.group(1) or ""
        if (_hedged(body, hit.start()) or _TRAILING_NEGATION.search(subject)
                or _LEADING_CONDITION.search(subject)):
            continue
        return {"from": [subject], "to": [hit.group(2)]}
    return None


def _hedged(body: str, start: int) -> bool:
    """Whether the clause just before a change verb denies or conditions it."""
    window = body[max(0, start - 8):start]
    return bool(_NEGATION.search(window) or _CONDITION.search(window))


def keeps_legal_entity(statement: str | None) -> bool | None:
    """Whether the absorbed unit keeps its legal person, where the sentence says.

    「保留四分法人主体」 keeps it; 「不再保留一分法人主体」 does not. Wording that leaves it
    undecided says so and gets nothing: 「尚未确定是否保留…」、「拟保留…」 and 「若保留…」 are
    not a keep, and neither is a silence — this never guesses from the direction of a merge.
    """
    body = re.sub(r"\s+", "", str(statement or ""))
    clause = next((part for part in re.split(r"[，。；]", body) if "法人" in part), "")
    if not clause or any(mark in clause for mark in _UNCERTAIN) or _CONDITION.search(clause):
        return None
    if _ABANDONS.search(clause):
        return False
    if _KEEPS.search(clause):
        return True
    return None


def same_end(left: str | None, right: str | None, aliases: dict | None = None) -> bool:
    """Whether two names are one end — only on evidence that says so.

    Equality is enough. A short form is the same end only when the document itself registers
    it as an alias of that name: 「智信」 is the sentence's way of saying 「天水智信」 only if
    an entry carries it as an alias. A short name that is merely *absent* from the registry
    proves nothing — 「财务部」 is not 「华北财务部」 just because only the long form is
    registered — so without an alias relation the answer is no.
    """
    left, right = str(left or ""), str(right or "")
    if not left or not right:
        return False
    if left == right:
        return True
    if not isinstance(aliases, dict):
        # A bare list of names is a name list, not an alias map: it says which names exist,
        # not which of them is the short form of another. A third review probed
        # `same_end("华北财务部", "财务部", known=["华北财务部"])` and was right that "only the
        # long form is registered" proves nothing — so a list settles no identity either.
        return False
    return right in (aliases.get(left) or ()) or left in (aliases.get(right) or ())


def merge_ends(current: list[str], parsed: list[str], aliases: dict | None = None,
               unresolved: list | None = None) -> list[str]:
    """Keep the candidate's own spelling of an end, add the ones only the sentence has.

    Three cases per parsed end, and nothing is guessed:

    * the candidate already names it (or registers it as an alias) — the canonical name stays;
    * it merely *looks like* an end the candidate has ("智静" beside "天水智静", "财务部" beside
      "华北财务部") — no fold and no addition: the candidate's name stays, and the pair is
      handed to ``unresolved`` so a reader can check the identity somewhere that has evidence;
    * it is a name the candidate does not have at all — it is added, because the sentence
      states it and nothing contradicts it.
    """
    out: list[str] = []
    for end in parsed:
        named = next((old for old in current if same_end(old, end, aliases)), None)
        if named:
            out.append(named)
            continue
        lookalike = next((old for old in current
                          if old and old != end and (old.endswith(end) or end.endswith(old))), None)
        if lookalike:
            if unresolved is not None:
                unresolved.append({"recorded": lookalike, "sentence": end})
            out.append(lookalike)
            continue
        out.append(end)
    for old in current:
        if old and not any(same_end(old, end, aliases) for end in out):
            out.append(old)
    return out


def layout_evidence(band_holder: str | None, band_locator: str | None,
                    source_id: str | None = None) -> dict | None:
    """The citation a layout-bound duty owes: the box it sits beside.

    A duty read off the row it shares with a unit does not name that unit in its own
    sentence, and a consumer asking "who is this for?" looks for the holder in the
    row's own quotes. A binding that a reader is meant to use therefore has to cite the
    box, or the answer stays right and unreadable (`holder_not_in_own_quote`).

    Only the page's own wording is returned — the quote is the box's text and the span
    hash is that text's — so nothing is invented here. No box, no citation.
    """
    holder = str(band_holder or "").strip()
    locator = str(band_locator or "").strip()
    if not holder or not locator:
        return None
    return {"locator": locator, "quote": holder, "source_id": source_id,
            "span_sha256": hashlib.sha256(holder.encode("utf-8")).hexdigest()}


def local_end_reference(short: str | None, sentence: str | None, row_arrows: list[dict],
                        from_names: list[str], page_names: list[str]) -> tuple[dict | None, str]:
    """Which box, in the sentence's own row, the short name can only mean here.

    A page prints "四分公司合并到智静" beside the arrow 四分公司 → 天水智静, and the reader
    of that sentence has to know that 「智静」 means the box the arrow points at. That is a
    reading of *this sentence on this row*, not a claim that the short form is the unit's
    name everywhere: the same characters in another document, another page or another
    period say nothing. So nothing here is registered as an alias, and a caller must keep
    the short form and the full name side by side.

    Everything that could make the reading wrong is a refusal instead of a binding:

    * the short form is not in the sentence, or is itself one of the change's own ends;
    * the page carries more than one name that contains the short form;
    * the row does not carry exactly one drawn arrow, or its ends do not name exactly one
      of the change's absorbing units (direction unclear);
    * the arrow's other end does not contain the short form, or is the short form itself.

    ``row_arrows`` are the arrows whose two end boxes sit on the sentence's band; the
    caller does the geometry, so this stays a decision over names and rows.
    """
    text = re.sub(r"[\s\u3000]+", "", str(sentence or ""))
    body = re.sub(r"[\s\u3000]+", "", str(short or ""))
    if not body or body not in text:
        return None, "句中没写这个短名，没有可消解的指代"
    froms = [re.sub(r"[\s\u3000]+", "", str(name or "")) for name in from_names or ()]
    if any(name and name == body for name in froms):
        return None, f"「{short}」本身就是这次变更的一端，不是需要消解的短名"
    page = [str(name or "") for name in page_names or () if str(name or "").strip()]
    candidates = [name for name in page if body in re.sub(r"[\s\u3000]+", "", name)]
    if len(candidates) > 1:
        return None, (f"本页有 {len(candidates)} 个名字含「{short}」"
                      f"（{'、'.join(sorted(set(candidates)))}）：局部不唯一，不能绑")
    if not candidates:
        return None, f"本页没有名字含「{short}」，只能等登记"
    arrows = [arrow for arrow in row_arrows or () if len(arrow.get("ends") or ()) == 2]
    if len(arrows) != 1:
        return None, f"这一句所在横带有 {len(arrows)} 条连线，指不到唯一那一条"
    arrow = arrows[0]
    ends = [{**end, "text": re.sub(r"[\s\u3000]+", "", str(end.get("text") or ""))}
            for end in arrow["ends"]]
    absorbing = [end for end in ends if end["text"] and end["text"] in froms]
    if len(absorbing) != 1:
        return None, ("箭头两端都不是句子写明的并入方" if not absorbing
                      else "箭头两端都是并入方，方向不清")
    source = absorbing[0]
    target = next(end for end in ends if end is not source)
    if not target["text"]:
        return None, "箭头的另一端没有名字"
    if target["text"] == body:
        return None, "箭头另一端就写着这个短名本身，不需要消解"
    if body not in target["text"]:
        return None, f"箭头另一端是「{target['text']}」，不含句中的「{short}」"
    return {"short": short, "full": target["text"], "arrow": arrow.get("locator"),
            "from": {"name": source["text"], "locator": source.get("locator")},
            "to": {"name": target["text"], "locator": target.get("locator")},
            "why": (f"本页只有「{target['text']}」含「{short}」，且「{source['text']}」到"
                    f"「{target['text']}」的连线正落在这一句所在横带（{arrow.get('locator')}）："
                    f"句中的「{short}」指「{target['text']}」——这是本句本行内的局部指代，"
                    f"不是全文档别名")}, ""


def stage_undistinguished(from_: list[str], to: list[str]) -> dict | None:
    """The names whose role before and after a change is not told apart.

    A change may keep a name: a surviving unit keeps its own, and an integration can print
    the same name on both sides. What such a record lacks is not legality but which stage
    each presence belongs to — which one ends, which one continues, which one is set up
    under that name. The answer is therefore "not decided yet", and it says so; nothing here
    makes an event with a repeated name invalid.
    """
    shared = [name for name in (from_ or []) if name in (to or [])]
    if not shared:
        return None
    return {"names": shared,
            "why": (f"「{'、'.join(shared)}」在变更前后都出现：保留名称的存续方是允许的，缺的是"
                    f"变更前后各自的角色或阶段（哪一个是终止方、哪一个是存续或新设方），"
                    f"现有字段分不开；事件资格待确认")}


def supersede_unknown(resolution: dict | None, by: list[str], note: str = "") -> dict | None:
    """The explicit reference from an old UNKNOWN to what answered it.

    A resolved question is not deleted: the record stays so a reader can see it was
    asked, but it points at the entries that answered it, and says in its own reason
    that it is history. One answer keeps a plain id; several keep the list.

    ``note`` says what the answers do not cover. A reference to entries that are
    themselves still pending answers less than the whole question, and a record that says
    "resolved" without that qualifier is the same over-claim as before.
    """
    if not resolution or resolution.get("class") == "remaining" or not by:
        return None
    reason = (f"classes_v1.3:这条问题已由 {len(by)} 条候选回答"
              f"（{('、'.join(by))[:120]}）；本行保留为历史，不再作为当前拒答依据")
    if note:
        reason += f"；{note}"
    return {"superseded_by": by[0] if len(by) == 1 else list(by), "reason": reason}


def narrow_absence_claim(statement: str | None) -> str | None:
    """An absence claim about a page is only ever a claim about its text.

    「页面另列…未说明二者与两种驱动模式的对应关系」 was written about a page whose two
    columns do show the correspondence: what the reader of the text cannot see is not
    what the page lacks. The claim is narrowed to the text, and the visual check stays
    open instead of being answered by a sentence that never looked.
    """
    body = str(statement or "").strip()
    if not body:
        return None
    hit = _ABSENCE_DIRECT.search(body)
    if hit is None:
        hit = _ABSENCE_AFTER_CLAUSE.search(body)
    if hit is None:
        return None
    if any(word in body for word in ("文本未明说", "版式")):
        return None
    narrowed = body[:hit.start()] + "文本" + body[hit.start() + 2:]
    return narrowed + "；版式上的对应关系需核对原页，不能读成「页面没有说明」"
