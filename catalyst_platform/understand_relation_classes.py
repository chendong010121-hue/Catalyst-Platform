"""What a relation on an org-chart page is allowed to mean.

`RELATION-CLASSES-v1.1.md` (Owner-reviewed, frozen) settles six things this module makes
concrete, because each one was a defect found by a human review of a real card.
`RELATION-CLASSES-v1.2.md` adds the corrections a full 349-row review of a second card
reproduced: a connector that exists is never reported as missing, the object and the agent
are read by meaning rather than word order, a negation or a condition is kept instead of
turned into a positive duty, "合并到" is an action and not a state, and a duty cell that
covers a whole group asks for the group instead of the nearest member.

The v1.1 six:

* "no path" is not "direct" — a direct superior needs an adjacent line or a sentence that
  says so; without either the relation is unknown, not direct.
* a state verb is not a state: "已合并为" is done, "需要整合为" is a plan, and a bare
  "设置为" only reads as a plan when the page's own words make it one.
* a quoted sentence makes a relation TEXT, not correct: subject, object, direction,
  condition, negation and pronoun scope each get checked.
* a drawn line into a governance body fixes no predicate on its own; a sentence that says
  "向 X 汇报" does, and recording it grants no authority.
* a reporting line may end at a committee or an organisation, not only at a post.
* 下设 is an organisation-setting relation with a fixed direction (parent → child) and is
  the inverse of 隶属 (child → parent); one pair carries one of the two, never both.

Nothing here reads a file or calls a model: it decides what a candidate row may claim
given the text it cites and the lines the page draws.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

CLASS_SET_VERSION = "relation-classes.v1.2"

# The closed set this material is processed under. A row outside it is not a relation
# this pass asserts; it becomes a duty or a question.
PREDICATES = ("隶属", "下设", "投资关联", "汇报", "负责", "产出")
INVERSE = {"下设": "隶属", "隶属": "下设"}
INVESTMENT_BAND = "对外投资单位"

SOURCE_DIRECT = "observed_from_source"
INFERRED = "inferred"
UNRESOLVED = "unresolved"

# Verbs that put a relation in one of the closed classes. Longest first so "下设" wins
# over "设" and "汇报" over "报".
_VERBS: tuple[tuple[str, str], ...] = (
    ("下设", "下设"), ("分设", "下设"),
    ("汇报", "汇报"), ("报请", "汇报"),
    ("负责", "负责"), ("主管", "负责"), ("统筹", "负责"),
    ("产出", "产出"), ("形成", "产出"), ("编制", "产出"), ("制定", "产出"),
    ("隶属", "隶属"), ("属于", "隶属"),
)

# §2: completed first, then plan, then the bare set-verbs that only count in a proposal.
_COMPLETED = ("已合并", "已成立", "已设置", "已整合", "已拆分", "此前", "现行", "现有", "目前已", "已经在")
_PLAN = ("拟", "计划", "将", "下一步", "建议", "需要", "应当", "拟设", "规划", "展望", "待")
_SET_VERBS = ("设置为", "整合为", "合并为", "拆分为", "设为", "合并到", "整合进")
_DONE_VERBS = tuple(dict.fromkeys(
    [verb for verb, _ in _VERBS] + list(_SET_VERBS) + ["合并", "成立", "下设", "隶属"]))
# "已隶属" / "已整合" — the finished-ness is in "已", not in the verb, so the marker is
# matched against any verb of the set instead of listing one phrase per verb.
_DONE = re.compile(r"已(?:经)?[^，。；]{0,4}(?:" + "|".join(re.escape(v) for v in _DONE_VERBS) + ")")
_NEGATION = ("不", "未", "没有", "并非", "不曾", "不予")
_CONDITION = ("如果", "若", "假如", "一旦", "在…情况下", "在……情况下")
_PRONOUN = ("其", "该", "上述", "前述", "本部门", "本单位", "该公司")

# Characters a clause may be read across when looking for the subject next to the verb.
_CLAUSE = re.compile(r"[。；;！!？?\n\r]+")


def _flat(text: str) -> str:
    """The text as it reads: no spaces, and one kind of bracket.

    Brackets are normalised because the same label is printed either way — "党委办公室
    （宣传部）" in a box, "(宣传部)" in a sentence — and comparing the two forms as
    different names is how one entity becomes two.
    """
    text = re.sub(r"[\s\u3000]+", "", str(text or ""))
    return text.replace("（", "(").replace("）", ")")


_BRACKETED = re.compile(r"([^()]+)[(]([^()]+)[)]")


def name_forms(text: str | None) -> tuple[str, ...]:
    """The spellings that name one thing: the label, and the alias its bracket carries.

    A post labelled "总工程师（技术副经理）" is written "总工程师：" in the cell beside it,
    and a centre labelled "技术研发中心（质量技术部）" is written "技术研发中心" in the
    sentence that sets it up. One thing, two names: a sentence that writes either has named
    the holder, and refusing it because the bracket is missing splits one entity into two.
    """
    flat = _flat(text)
    if not flat:
        return ()
    forms = [flat]
    match = _BRACKETED.fullmatch(flat)
    if match:
        for part in (match.group(1).strip(), match.group(2).strip()):
            if len(part) >= 2 and part not in forms:
                forms.append(part)
    return tuple(forms)


def _named_in(text: str, flat_word: str) -> bool:
    return any(form in flat_word for form in name_forms(text))


def closed_predicate(raw: str | None, sentence: str = "", *, allow_raw_fallback: bool = True) -> str | None:
    """The closed-set predicate this row may carry, or None when nothing fits.

    The sentence decides first: "向变革委员会汇报" is a reporting line whatever the row
    called it (the review found it recorded as 负责). The declared value is the fallback,
    for rows whose evidence is a drawing and whose wording the reader chose.
    """
    clause = _flat(sentence)
    for verb, predicate in _VERBS:
        if verb in clause:
            return predicate
    if not allow_raw_fallback:
        # A sentence that says what happened, with no verb from the closed set, is a row
        # the set cannot carry: "研讨确定" is not "产出" and must not be rounded to it.
        return None
    text = _flat(raw or "")
    if text in PREDICATES:
        return text
    for verb, predicate in _VERBS:
        if verb in text:
            return predicate
    return None


_PLAN_ACTION = re.compile(r"计划(?:于|在|将|要|对|把|\d|[一二三四五六七八九十]|整|合|推|开|建|实|进|做|完|优|调|编制|组织|开展)")
_DIRECTIONAL = ("合并到", "整合进", "整合到")


def _near_negation(clause: str, index: int) -> bool:
    """Whether a negation mark sits within two characters before ``index``."""
    head = clause[max(0, index - 3):index]
    return any(mark in head for mark in _NEGATION)


def sentence_state(text: str, *, proposal_context: bool = False) -> tuple[str | None, str]:
    """Which state one sentence states, with the words that decided it.

    v1.2 §R4.4: negation is its own dimension. It does not wipe the state — "未设置为 X"
    still says the setup was planned, and "不需要负责 X" says nothing about state at all;
    what decides is whether a plan or a set-verb survives the negation.
    v1.2 §R5.2: "合并到" only names an action. Completed needs 已/已经; a plan needs 拟/将.
    v1.2 §R5.3: a noun that happens to be called 计划 ("年度经营计划") yields no tense, but
    a real "计划 + action" in the same sentence still does.
    """
    clause = _flat(text)
    if not clause:
        return None, "没有句子"
    negated = any(mark in clause for mark in _NEGATION)
    for mark in _COMPLETED:
        if mark in clause:
            return "as-is", f"完成/既成（{mark}）"
    finished = _DONE.search(clause)
    if finished:
        return "as-is", f"完成/既成（{finished.group(0)}）"
    planned = ""
    for mark in _PLAN:
        if mark == "计划":
            hit = _PLAN_ACTION.search(clause)
            if hit and not _near_negation(clause, hit.start()):
                planned = mark
                break
            continue
        index = clause.find(mark)
        if index < 0:
            continue
        if mark in ("将",) and index == 0:
            planned = mark
            break
        if _near_negation(clause, index):
            continue
        planned = mark
        break
    if planned:
        return "to-be", f"方案语气（{planned}）"
    for mark in _SET_VERBS:
        if mark not in clause:
            continue
        if mark in _DIRECTIONAL:
            # "合并到" is an action, not a state: only 拟/已 in front of it says which.
            return None, f"只给动作（{mark}），不给状态"
        if proposal_context:
            return "to-be", f"设置类动词（{mark}）+ 页面为方案语境"
        tail = "，且句子里有否定" if negated else ""
        return None, f"设置类动词（{mark}）但看不出是方案还是既成{tail}"
    if negated:
        return None, "否定句，且没有可判状态的依据"
    return None, "句子没有状态词"


def actor_role(sentence: str, subject: str, obj: str, predicate: str) -> tuple[str, str]:
    """Who the sentence makes the agent, by meaning rather than by word order.

    "财务部负责付款凭证核验" and "付款凭证由财务部核验" put the two ends in different
    places and say the same thing; both make 财务部 the agent. Returns
    ``("agent" | "reversed" | "unknown", <who the sentence names>)`` — an unknown role is
    a question, never an accusation that the row runs backwards (§R2.3).
    """
    flat = _flat(sentence)
    subject_forms = name_forms(subject)
    obj_forms = name_forms(obj)

    def names_any(text: str, forms: Sequence[str]) -> bool:
        return any(form and form in text for form in forms)

    if predicate == "汇报":
        match = re.search(r"([^，。；]{1,24}?)向([^，。；]{1,24}?)汇报", flat)
        if not match:
            return "unknown", ""
        reporter, receiver = match.group(1), match.group(2)
        if names_any(reporter, subject_forms) and names_any(receiver, obj_forms):
            return "agent", subject
        if names_any(reporter, obj_forms) and names_any(receiver, subject_forms):
            return "reversed", obj
        return "unknown", reporter

    verb_at = flat.find("负责")
    if verb_at < 0:
        return "unknown", ""
    head = flat[:verb_at]
    by = re.search(r"由([^，。；]{1,24})$", head)
    if by:
        who = by.group(1)
        if names_any(who, subject_forms):
            return "agent", subject
        if names_any(who, obj_forms):
            return "reversed", obj
        return "unknown", who
    for form in sorted(subject_forms, key=len, reverse=True):
        if form and head.endswith(form):
            return "agent", subject
    for form in sorted(obj_forms, key=len, reverse=True):
        if form and head.endswith(form):
            return "reversed", obj
    if names_any(head, subject_forms) and not names_any(head, obj_forms):
        return "agent", subject
    if names_any(head, obj_forms) and not names_any(head, subject_forms):
        return "reversed", obj
    return "unknown", head[-8:]


def binding_issues(sentence: str, subject: str, obj: str | None) -> tuple[str, ...]:
    """What stops this sentence from supporting (subject → object), one token each."""
    text = str(sentence or "")
    flat = _flat(text)
    issues: list[str] = []
    if not flat:
        return ("sentence_absent",)
    if _flat(subject) and not _named_in(subject, flat):
        issues.append("subject_absent")
    if obj and _flat(obj) and not _named_in(obj, flat):
        issues.append("object_absent")
    if obj and not _named_in(obj, flat) and any(_flat(obj).endswith(mark) or mark in _flat(obj) for mark in _PRONOUN):
        issues.append("pronoun_object")
    if any(mark in flat for mark in _CONDITION):
        issues.append("conditional")
    if obj:
        # "未设…" / "不属于…": any spelling of the object counts, not just the long one.
        alternatives = "|".join(re.escape(form) for form in name_forms(obj))
        if alternatives and any(re.search(re.escape(mark) + r"[^，。；]{0,6}(?:" + alternatives + ")", flat)
                                for mark in _NEGATION):
            issues.append("negated")
    return tuple(dict.fromkeys(issues))


def holding_clause(sentence: str, obj: str) -> str:
    """The clause of the quote that carries the object — the only one a subject may come from."""
    for clause in _CLAUSE.split(str(sentence or "")):
        if obj and _named_in(obj, _flat(clause)):
            return clause
    return ""


@dataclass(frozen=True)
class Judgement:
    """What one candidate relation may claim, and what stops it when it may not."""
    predicate: str | None
    evidence_class: str
    scope_state: str | None
    verdict: str            # "assert" | "ask"
    why: str
    question: str | None = None
    # The sentence runs parent → child while the row wrote child → parent: §1 fixes the
    # direction of 下设, so the caller writes the row with its two ends the other way round.
    swapped: bool = False
    # v1.2 §R4: a qualifier is information, not a reason to throw the sentence away —
    # "财务部不负责审批" is a sourced fact the contract has no slot for yet.
    qualifier: str = ""      # "negated" | "conditional" | ""
    # v1.2 §R1: which of the three facts this row rests on — a raw connector, a path to a
    # unit, or a meaning the source states. Only "meaning" may assert.
    tier: str = ""           # "raw" | "path" | "meaning" | ""

    @property
    def assertable(self) -> bool:
        return self.verdict == "assert"


def direction_fixed(predicate: str | None, sentence: str, subject: str, obj: str) -> bool:
    """Whether a 下设 sentence names the row's object as the parent and its subject as the child.

    "…设置为市场营销中心，下设招投标部、策划部、投资管理部" has a fixed direction, and a
    card that wrote 投资管理部 → 市场营销中心 chose the 隶属 direction for words that say
    下设. The sentence decides which end is the parent, so the row is corrected rather than
    dropped (§6: 方向反了就改正，判不出就提问).
    """
    if predicate != "下设" or not _flat(subject) or not _flat(obj):
        return False
    clause = _flat(sentence)
    cut = clause.find("下设")
    if cut < 0:
        return False
    before = clause[:cut]
    return _flat(obj) in before and _flat(subject) not in before


def judge_relation(*, subject: str, obj: str, sentence: str, drawn: bool,
                   path: Sequence[str] = (), page_state: str | None = None,
                   proposal_context: bool = False, raw_predicate: str | None = None,
                   governance: bool = False, positions: bool = False,
                   band_object: str = "", raw_edge: str = "",
                   direction_note: str = "") -> Judgement:
    """One row, decided.

    ``sentence`` is the text the row cites — **one item**, not a whole cell: a cell of seven
    numbered items still supports each of them separately, and passing the whole cell lets
    one item's subject vouch for another's. ``band_object`` names the column heading the
    row put at its far end ("中台部门"): a column is not an organisation, so that row asks
    which unit the relation flattens onto instead of reading "belongs to the column".
    """
    steps = tuple(str(step) for step in path if step)
    investment = INVESTMENT_BAND in {_flat(step) for step in steps} or INVESTMENT_BAND == _flat(obj)
    predicate = closed_predicate(raw_predicate, sentence, allow_raw_fallback=not sentence)

    if sentence:
        issues = binding_issues(sentence, subject, obj)
        if "negated" in issues:
            return Judgement(None, UNRESOLVED, None, "ask", "原文是否定句，关系没有成立",
                             f"原文是否定句（{obj}）。{subject} 与 {obj} 到底是什么关系？")
        if "conditional" in issues:
            return Judgement(None, UNRESOLVED, None, "ask", "原文带条件，不能当无条件关系",
                             f"原文对 {subject} 与 {obj} 的关系设了条件，成立条件是什么？")
        if "subject_absent" in issues:
            clause = holding_clause(sentence, obj) or sentence
            # The verb is readable even when the subject is not: "向变革委员会汇报决策" is a
            # reporting line whose reporter is unstated, and calling it 负责 would turn the
            # receiver into the object of a responsibility (review 57).
            return Judgement(predicate, UNRESOLVED, None, "ask",
                             f"主语不在承载这一条的分句里（分句：{clause.strip()[:40]}）",
                             f"「{clause.strip()[:40]}」这一条没有写明由谁负责或谁向谁汇报，请补齐。")
        if "object_absent" in issues and "pronoun_object" in issues:
            return Judgement(None, UNRESOLVED, None, "ask", "宾语是指代，且指代对象不在同一句",
                             f"{subject} 对应的对象用了代词，指的是谁？")
        if "object_absent" in issues:
            # §R2.1: the clause carries the subject but never names the object it is
            # attached to — the sentence supports no relation between these two ends.
            clause = holding_clause(sentence, subject) or sentence
            return Judgement(predicate, UNRESOLVED, None, "ask",
                             f"对象不在这一条里（分句：{clause.strip()[:40]}）",
                             f"「{clause.strip()[:40]}」这一条说的是谁与谁的关系？对象没有写出来。")
        state, why_state = sentence_state(sentence, proposal_context=proposal_context)
        state = state or page_state
        if predicate in ("负责", "汇报"):
            role, who = actor_role(sentence, subject, obj, predicate)
            if role == "reversed":
                return Judgement(predicate, UNRESOLVED, state, "ask",
                                 f"句子里的{'报告方' if predicate == '汇报' else '负责人'}是「{who}」，行写反了",
                                 f"句子里是「{who}」，这条关系要不要改成反向（{obj} → {subject}）？")
            if role == "unknown":
                return Judgement(predicate, UNRESOLVED, state, "ask",
                                 "句子没有点明谁是负责人或报告方",
                                 f"「{sentence.strip()[:40]}」里，谁负责、谁向谁汇报？")
        if predicate is None:
            return Judgement(None, UNRESOLVED, state, "ask", "原文的动词不在闭集里，也没有可对应的类别",
                             f"「{sentence.strip()[:40]}」这条关系的谓词该怎么记？")
        if investment and predicate == "隶属":
            predicate = "投资关联"
        swapped = direction_fixed(predicate, sentence, subject, obj)
        if state is None:
            return Judgement(predicate, INFERRED, None, "ask", f"状态判不出（{why_state}）",
                             f"{subject} → {obj} 这条是现状还是调整后的？", swapped)
        return Judgement(predicate, SOURCE_DIRECT, state, "assert", f"原文直陈（{why_state}）",
                         None, swapped, tier="meaning")

    # No sentence: only the drawing can speak, and it speaks about belonging, not about
    # duties or outputs.
    if not drawn:
        if raw_edge:
            # §R1.3/R1.4: the connector is there; what is missing is the meaning. Saying
            # "no line" here is the defect the review found 41 times on one card.
            note = f"；{direction_note}" if direction_note else ""
            return Judgement(None, UNRESOLVED, page_state, "ask",
                             f"线在（{raw_edge}），但这条线记什么关系、朝哪边，原文没定{note}",
                             f"「{subject}」与「{obj}」之间这条线（{raw_edge}）该记成哪种关系、方向如何？",
                             tier="raw")
        return Judgement(None, UNRESOLVED, page_state, "ask", "原文没有这句话，页面也没有画出这条线",
                         f"{subject} 与 {obj} 之间的关系，原文依据在哪里？", tier="none")

    def drawn_claim(predicate: str, why: str, question: str) -> Judgement:
        """A claim read off the drawing: assertable only on a page that says which state."""
        note = "" if page_state else "；本页没有声明现状还是调整后"
        return Judgement(predicate, INFERRED, page_state, "assert" if page_state else "ask",
                         why + note, None if page_state else question,
                         tier="meaning" if page_state else "path")

    if positions:
        # Two posts joined by a line report to one another; "隶属" would flatten a
        # reporting line into membership of the unit, which the drawing does not say.
        return drawn_claim("汇报", "两端都是岗位，画出来的是一条汇报线",
                           f"{subject} 与 {obj} 的汇报线是现状还是调整后的？")
    if band_object:
        # A column heading groups units by function; it is not an organisation a unit can
        # belong to (§4). The drawing proves the line, not that the column is the parent.
        return Judgement(None, UNRESOLVED, page_state, "ask",
                         f"对象「{band_object}」是分类列，不是单位",
                         f"{subject} 折平到「{band_object}」之上的哪个单位？")
    if governance:
        # A line into the board or a management layer draws a governance relation; which
        # one it is (产生/监督/被汇报) the drawing does not say, so the row asks.
        return Judgement(None, UNRESOLVED, page_state, "ask",
                         "图线连到治理层，单凭连线定不了谓词",
                         f"{subject} 与 {obj} 之间是治理关系（谁对谁负责决策、谁产生谁），请给出记录口径？")
    if investment:
        return drawn_claim("投资关联", "画出来的线穿过「对外投资单位」：只能说到投资关联",
                           f"{subject} 与 {obj} 的投资关联属于现状还是调整后？")
    if steps and len(steps) > 2:
        return drawn_claim("隶属", f"画出来的线穿过 {len(steps) - 2} 个中间格：" + " → ".join(steps),
                           f"{subject} 属于 {obj} 是现状还是调整后的？")
    if len(steps) == 2:
        return drawn_claim("隶属", "两端直接相邻的连线",
                           f"{subject} 与 {obj} 的上下关系是现状还是调整后的？")
    return Judgement(None, UNRESOLVED, page_state, "ask", "只有连线、没有可复算的路径",
                     f"{subject} 与 {obj} 的连线经过哪些格子？")


def direct_superior(judgement: Judgement, path: Sequence[str], sentence: str, subject: str, obj: str) -> str:
    """`direct` / `indirect` / `unknown` — the distinction §4 of the standard insists on.

    A short path is not evidence of a direct line: only an adjacent drawing or a sentence
    that names both ends without stepping through anything says "direct".
    """
    steps = tuple(str(step) for step in path if step)
    if sentence and _named_in(subject, _flat(sentence)) and _named_in(obj, _flat(sentence)):
        return "direct"
    if len(steps) == 2:
        return "direct"
    if len(steps) > 2:
        return "indirect"
    return "unknown"


def layout_binds(cell: tuple[int, int, int, int] | None,
                 box: tuple[int, int, int, int] | None,
                 others: Sequence[tuple[int, int, int, int]] = ()) -> bool:
    """Whether a post's box and the cell beside it are one row on the page.

    ``(x, y, cx, cy)`` for both, in the page's own units. Same row means their vertical
    spans overlap by at least half the shorter box, and adjacent means no third box sits
    between them in that row — the note to the left of a department and the note to its
    right are both its own, but the row above is not: a review found a 中台 department
    carrying the 后台 department's "服务" note, and the note one row up carrying the
    other's "管理+赋能".
    """
    if not cell or not box:
        return False
    cx, cy, cw, ch = cell
    bx, by, bw, bh = box
    overlap = min(cy + ch, by + bh) - max(cy, by)
    if overlap <= 0 or overlap < 0.5 * min(ch, bh):
        return False
    left_edge, right_edge = (cx + cw, bx) if cx < bx else (bx + bw, cx)
    for ox, oy, ow, oh in others:
        if (ox, oy, ow, oh) in (tuple(cell), tuple(box)):
            continue
        same_row = min(oy + oh, cy + ch) - max(oy, cy)
        if same_row <= 0 or same_row < 0.5 * min(oh, ch):
            continue
        if ox + ow <= left_edge or ox >= right_edge:
            continue
        return False
    return True


_DUTY_MARKS = ("负责", "承担", "主管", "统筹", "参与", "审核", "审批", "执行", "管理", "设置",
               "保留", "推进", "组织", "协调", "编制", "制定", "落实")
_NEGATED_DUTY = re.compile(r"(?:不再|无需|不予|不必|不需要|不负责|未负责|没有负责|不承担|未承担)"
                           r"[^，。；]{0,6}(?:" + "|".join(re.escape(v) for v in _DUTY_MARKS) + ")")
# §R4: a duty sentence that says when or for what it applies is not an unconditional duty.
# The marks below are the ones this material actually uses, each pinned by a test:
#   "…新业务培育起来之后，可成立子公司"        — afterwards: only once something has happened
#   "分公司有资源，或便于在区域开展的新业务"   — either/or: one of two scopes
#   "业务规模足够大，专业性足够强"             — a threshold of size or skill
#   "可在公司层面设置 / 可以通过…模式运作"     — one way of doing it, not the only one
# A word that only looks conditional is not one: "具有" in "需具有一定的稳定性" is a
# property, and a post's duty ("总工程师：负责…") carries no scope clause at all.
_CONDITION_DUTY = re.compile(
    r"(?:如果|若|如遇|如需|一旦|视情况"
    r"|在[^，。；]{0,8}(?:期间|情况下|时)"
    r"|[^，。；]{1,12}之后[，,]?"
    r"|足够(?:大|强|多|高|好)"
    r"|，或(?:便于|需要|在|由|经|视)"
    r"|可(?:以)?(?:在|通过|由|成立|设置|放在|放到|置于|按|视|根据))")


def duty_qualifier(sentence: str) -> tuple[str, str]:
    """Whether a duty sentence is negated or conditional, and the words that said so.

    v1.2 §R4: the point is never to turn "财务部不负责审批" into a positive duty. The
    sentence stays where it is; this only says which qualifier the row carries.
    """
    flat = _flat(sentence)
    hit = _NEGATED_DUTY.search(flat)
    if hit:
        return "negated", hit.group(0)
    hit = _CONDITION_DUTY.search(flat)
    if hit:
        return "conditional", hit.group(0)
    return "", ""


def judge_duty(*, holder: str | None, sentence: str, holder_known: bool,
               layout_bound: bool = False, layout_ref: str = "",
               band_holder: str = "", grouped: bool = False) -> Judgement:
    """A duty belongs to someone the sentence names — otherwise it is a task without an owner.

    A page that prints a post in a box and its duties in the cell beside it binds them by
    layout, not by prose; that binding is accepted only when the boxes really share a row
    (`layout_binds`), never because the boxes are merely near each other. ``band_holder`` is
    the post the layout actually puts in this row, when it is not the one the row claims.
    """
    text = str(sentence or "")
    flat = _flat(text)
    qualifier, marks = duty_qualifier(text)
    if qualifier == "negated":
        return Judgement(None, UNRESOLVED, sentence_state(text)[0], "ask",
                         f"否定句（{marks}）：这一条不是在做这件事，原句保留",
                         f"「{flat[:40]}」是“不负责/不再负责”，要不要为否定职责建条目？",
                         qualifier=qualifier)
    if qualifier == "conditional":
        # The condition is quoted, not paraphrased: whoever consumes the duty has to see
        # that it applies only then, and decide what it means outside the condition.
        return Judgement(None, UNRESOLVED, sentence_state(text)[0], "ask",
                         f"条件句（{marks}）：只在条件成立时才是职责，原句保留",
                         f"「{flat[:36]}」只在「{marks}」成立时才适用：按条件职责记，还是另有条件？",
                         qualifier=qualifier)
    named = bool(holder and _flat(holder) and _named_in(holder, flat))
    if grouped and not named:
        # §R6.3: a group may carry the duty — what the layout cannot do is name the
        # nearest member of it. The question says so without proposing a candidate.
        # A sentence that names the holder settles it without the layout, so grouping
        # only decides rows the sentence leaves open.
        return Judgement(None, UNRESOLVED, sentence_state(text)[0], "ask",
                         f"这一格在局部区域里挨着不止一个单位，版式定不了归谁（{layout_ref or '同一纵带'}）",
                         f"「{flat[:36]}」这一组里由谁承担，还是整组承担？")
    if (not holder or not _flat(holder) or not _named_in(holder, flat)) and layout_bound:
        state, _why = sentence_state(text)
        return Judgement("负责", INFERRED, state, "assert",
                         f"版式同一行：持有人盒子与这一格并排（{layout_ref or '同一纵带'}）")
    if not holder or not _flat(holder) or not _named_in(holder, flat):
        if band_holder and not _named_in(band_holder, _flat(holder)):
            return Judgement(None, UNRESOLVED, sentence_state(text)[0], "ask",
                             f"版式上这一格与「{band_holder}」同一行，与「{holder}」不同行",
                             f"这一格是「{band_holder}」的还是「{holder}」的职责？")
        return Judgement(None, UNRESOLVED, sentence_state(text)[0], "ask",
                         "负责人不在这一条里（可能是从相邻条目借来的）",
                         f"「{flat[:36]}」这件事由谁负责？")
    if not holder_known:
        return Judgement(None, UNRESOLVED, sentence_state(text)[0], "ask",
                         "负责人说得出来，但本文档没有把它声明成一个单位/岗位",
                         f"「{holder}」在这份材料里指的是哪个单位或岗位？")
    state, _why = sentence_state(text)
    return Judgement("负责", SOURCE_DIRECT, state, "assert", "同一条目里点明了负责人与自己要做的事")


def pair_conflicts(rows: Sequence[Mapping[str, object]]) -> list[str]:
    """Pairs carrying both directions of the same relation through the inverse pair.

    `下设 A→B` and `隶属 B→A` say one thing twice; §1 asks for one row per pair.
    """
    seen: dict[frozenset, set[str]] = {}
    for row in rows:
        predicate = str(row.get("predicate") or "")
        subject, obj = _flat(row.get("subject")), _flat(row.get("object"))
        if predicate not in INVERSE or not subject or not obj:
            continue
        seen.setdefault(frozenset((subject, obj)), set()).add(predicate)
    return [f"{sorted(pair)} 同时写了 {'/'.join(sorted(values))}"
            for pair, values in seen.items() if values == set(INVERSE)]
