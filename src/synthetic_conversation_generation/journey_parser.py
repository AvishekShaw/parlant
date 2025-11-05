"""
Journey Parser - Extract state machine structure from Parlant journey Python files.

This parser uses AST (Abstract Syntax Tree) analysis to extract:
- Journey metadata (title, description, conditions)
- States (tool_state and chat_state)
- Transitions with conditions
- Canned responses with templates and signals
- Guidelines with conditions and actions
"""

import ast
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import yaml

logger = logging.getLogger(__name__)


@dataclass
class CannedResponse:
    """Represents a canned response template"""
    template: str
    signals: List[str] = field(default_factory=list)


@dataclass
class Transition:
    """Represents a state transition"""
    condition: Optional[str] = None  # None = default transition
    next_state: str = ""


@dataclass
class JourneyState:
    """Represents a single state in the journey"""
    state_id: str
    state_type: str  # "chat_state" or "tool_state"
    description: Optional[str] = None  # For chat_state
    tool: Optional[str] = None  # For tool_state (function name)
    canned_responses: List[CannedResponse] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    comment: Optional[str] = None  # Comment from source file


@dataclass
class Guideline:
    """Represents a journey-level guideline"""
    condition: str
    action: str
    tools: List[str] = field(default_factory=list)


@dataclass
class Journey:
    """Represents a complete journey"""
    name: str
    description: str
    conditions: List[str]
    states: Dict[str, JourneyState]
    guidelines: List[Guideline]
    initial_state: str = "t1"  # Default to t1

    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "initial_state": self.initial_state,
            "states": {
                state_id: {
                    "state_id": state.state_id,
                    "state_type": state.state_type,
                    "description": state.description,
                    "tool": state.tool,
                    "comment": state.comment,
                    "canned_responses": [
                        {"template": cr.template, "signals": cr.signals}
                        for cr in state.canned_responses
                    ],
                    "transitions": [
                        {"condition": t.condition, "next_state": t.next_state}
                        for t in state.transitions
                    ]
                }
                for state_id, state in self.states.items()
            },
            "guidelines": [
                {
                    "condition": g.condition,
                    "action": g.action,
                    "tools": g.tools
                }
                for g in self.guidelines
            ]
        }

    def to_yaml(self, path: str):
        """Save journey to YAML file"""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False, width=120)
        logger.info(f"Saved journey to {path}")


class JourneyParser:
    """Parse Parlant journey Python files using AST analysis"""

    def __init__(self, journey_file_path: str):
        self.journey_file_path = journey_file_path
        self.source_code = None
        self.ast_tree = None
        self.states: Dict[str, JourneyState] = {}
        self.state_var_to_id: Dict[str, str] = {}  # Maps variable names to state IDs
        self.guidelines: List[Guideline] = []

    def parse(self) -> Journey:
        """
        Parse the journey file and extract complete state machine.

        Returns:
            Journey object with all states, transitions, and guidelines
        """
        logger.info(f"Parsing journey file: {self.journey_file_path}")

        # 1. Load and parse AST
        with open(self.journey_file_path, 'r') as f:
            self.source_code = f.read()

        self.ast_tree = ast.parse(self.source_code)

        # 2. Find create_journey function
        create_journey_func = self._find_create_journey_function()

        # 3. Extract journey metadata
        journey_metadata = self._extract_journey_metadata(create_journey_func)

        # 4. Extract states and transitions
        self._extract_states_and_transitions(create_journey_func)

        # 5. Extract guidelines
        self._extract_guidelines(create_journey_func)

        # 6. Build complete journey
        journey = Journey(
            name=journey_metadata["title"],
            description=journey_metadata["description"],
            conditions=journey_metadata["conditions"],
            states=self.states,
            guidelines=self.guidelines
        )

        logger.info(f"Parsed journey '{journey.name}' with {len(self.states)} states and {len(self.guidelines)} guidelines")

        return journey

    def _find_create_journey_function(self) -> ast.FunctionDef:
        """Find the create_journey async function in the AST"""
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "create_journey":
                return node
        raise ValueError("Could not find create_journey function in file")

    def _extract_journey_metadata(self, func_node: ast.AsyncFunctionDef) -> Dict[str, Any]:
        """Extract journey title, description, and conditions"""
        metadata = {
            "title": "",
            "description": "",
            "conditions": []
        }

        for node in ast.walk(func_node):
            # Look for: journey = await agent.create_journey(...)
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    if node.targets[0].id == "journey":
                        # Found journey creation
                        if isinstance(node.value, ast.Await):
                            call_node = node.value.value
                            if isinstance(call_node, ast.Call):
                                # Extract keyword arguments
                                for keyword in call_node.keywords:
                                    if keyword.arg == "title":
                                        metadata["title"] = ast.literal_eval(keyword.value)
                                    elif keyword.arg == "description":
                                        metadata["description"] = self._extract_string_value(keyword.value)
                                    elif keyword.arg == "conditions":
                                        metadata["conditions"] = ast.literal_eval(keyword.value)

        return metadata

    def _extract_states_and_transitions(self, func_node: ast.AsyncFunctionDef):
        """Extract all states and their transitions"""

        # First pass: extract all state assignments
        for stmt in func_node.body:
            if isinstance(stmt, ast.Assign):
                self._process_state_assignment(stmt)

        # Second pass: extract transitions that don't create new state variables (e.g., _ = ... or await ...)
        for stmt in func_node.body:
            if isinstance(stmt, ast.Assign):
                if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    if stmt.targets[0].id == "_":
                        # This is a transition without creating a new state
                        self._process_inline_transition(stmt)
            elif isinstance(stmt, ast.Expr):
                # Standalone await expressions (no assignment)
                if isinstance(stmt.value, ast.Await):
                    self._process_inline_transition_from_expr(stmt.value)

    def _process_state_assignment(self, assign_node: ast.Assign):
        """Process a state assignment like: t2 = await t1.target.transition_to(...)"""

        if len(assign_node.targets) != 1:
            return

        target = assign_node.targets[0]
        if not isinstance(target, ast.Name):
            return

        state_var = target.id

        # Skip non-state variables
        if state_var == "_" or state_var == "journey":
            return

        # Extract the transition_to call
        value = assign_node.value
        if isinstance(value, ast.Await):
            call_node = value.value
            if isinstance(call_node, ast.Call):
                # Check if this is a transition_to call
                if self._is_transition_to_call(call_node):
                    # Extract state info
                    state_info = self._extract_state_from_transition_call(call_node, state_var)

                    # Find comment above this assignment
                    comment = self._find_comment_for_line(assign_node.lineno)
                    state_info["comment"] = comment

                    # Create state object
                    state = JourneyState(
                        state_id=state_var,
                        state_type=state_info["state_type"],
                        description=state_info.get("description"),
                        tool=state_info.get("tool"),
                        canned_responses=state_info.get("canned_responses", []),
                        comment=comment
                    )

                    # Store state
                    self.states[state_var] = state

                    # Extract the source state (where this transition comes from)
                    source_state = self._extract_source_state(call_node)
                    if source_state:
                        # Add transition to source state
                        condition = state_info.get("condition")
                        transition = Transition(condition=condition, next_state=state_var)

                        if source_state in self.states:
                            self.states[source_state].transitions.append(transition)

    def _process_inline_transition(self, assign_node: ast.Assign):
        """Process inline transitions like: _ = await t5.target.transition_to(state=p.END_JOURNEY)"""

        value = assign_node.value
        if isinstance(value, ast.Await):
            self._extract_transition_from_await(value)

    def _process_inline_transition_from_expr(self, await_node: ast.Await):
        """Process standalone await transitions like: await t3.target.transition_to(state=p.END_JOURNEY)"""
        self._extract_transition_from_await(await_node)

    def _extract_transition_from_await(self, await_node: ast.Await):
        """Extract transition information from an await node"""
        call_node = await_node.value
        if isinstance(call_node, ast.Call):
            if self._is_transition_to_call(call_node):
                # Extract transition info
                source_state = self._extract_source_state(call_node)

                # Extract condition if present
                condition = None
                for keyword in call_node.keywords:
                    if keyword.arg == "condition":
                        condition = self._extract_string_value(keyword.value)

                # Check if this is END_JOURNEY transition
                for keyword in call_node.keywords:
                    if keyword.arg == "state":
                        if isinstance(keyword.value, ast.Attribute):
                            if keyword.value.attr == "END_JOURNEY":
                                # Add END transition to source state
                                if source_state and source_state in self.states:
                                    transition = Transition(condition=condition, next_state="END")
                                    self.states[source_state].transitions.append(transition)
                                    return

                # Or check if this is a transition to another state
                for keyword in call_node.keywords:
                    if keyword.arg == "state":
                        if isinstance(keyword.value, ast.Attribute):
                            # This might be a transition to another state's target
                            target_state = self._extract_state_reference(keyword.value)
                            if target_state and source_state and source_state in self.states:
                                transition = Transition(condition=condition, next_state=target_state)
                                self.states[source_state].transitions.append(transition)

    def _is_transition_to_call(self, call_node: ast.Call) -> bool:
        """Check if this is a transition_to() call"""
        if isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr == "transition_to"
        return False

    def _extract_source_state(self, call_node: ast.Call) -> Optional[str]:
        """Extract the source state from a transition_to call"""
        # Pattern: t1.target.transition_to() or journey.initial_state.transition_to()

        if isinstance(call_node.func, ast.Attribute):
            obj = call_node.func.value
            if isinstance(obj, ast.Attribute):
                # This is something.target or something.initial_state
                if obj.attr == "target":
                    # Get the state variable
                    if isinstance(obj.value, ast.Name):
                        return obj.value.id
                elif obj.attr == "initial_state":
                    # This is journey.initial_state
                    return None  # This is the first state

        return None

    def _extract_state_reference(self, attr_node: ast.Attribute) -> Optional[str]:
        """Extract state reference from expressions like t7.target"""
        if attr_node.attr == "target":
            if isinstance(attr_node.value, ast.Name):
                return attr_node.value.id
        return None

    def _extract_state_from_transition_call(self, call_node: ast.Call, state_var: str) -> Dict[str, Any]:
        """Extract state information from transition_to call"""
        state_info = {
            "state_type": None,
            "description": None,
            "tool": None,
            "condition": None,
            "canned_responses": []
        }

        for keyword in call_node.keywords:
            if keyword.arg == "chat_state":
                state_info["state_type"] = "chat_state"
                state_info["description"] = self._extract_string_value(keyword.value)

            elif keyword.arg == "tool_state":
                state_info["state_type"] = "tool_state"
                # Extract tool function name
                if isinstance(keyword.value, ast.Name):
                    state_info["tool"] = keyword.value.id
                elif isinstance(keyword.value, ast.List):
                    # Multiple tools
                    tools = [self._extract_name(t) for t in keyword.value.elts]
                    state_info["tool"] = ", ".join(tools)

            elif keyword.arg == "condition":
                state_info["condition"] = self._extract_string_value(keyword.value)

            elif keyword.arg == "canned_responses":
                state_info["canned_responses"] = self._extract_canned_responses(keyword.value)

        return state_info

    def _extract_canned_responses(self, list_node: ast.List) -> List[CannedResponse]:
        """Extract canned responses from list"""
        canned_responses = []

        for element in list_node.elts:
            # Each element is: await server.create_canned_response(...)
            if isinstance(element, ast.Await):
                call_node = element.value
                if isinstance(call_node, ast.Call):
                    template = None
                    signals = []

                    for keyword in call_node.keywords:
                        if keyword.arg == "template":
                            template = self._extract_string_value(keyword.value)
                        elif keyword.arg == "signals":
                            if isinstance(keyword.value, ast.List):
                                signals = [self._extract_string_value(s) for s in keyword.value.elts]

                    if template:
                        canned_responses.append(CannedResponse(template=template, signals=signals))

        return canned_responses

    def _extract_guidelines(self, func_node: ast.AsyncFunctionDef):
        """Extract journey guidelines"""

        for node in ast.walk(func_node):
            # Look for: await journey.create_guideline(...)
            if isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Await):
                    call_node = node.value.value
                    if isinstance(call_node, ast.Call):
                        if isinstance(call_node.func, ast.Attribute):
                            if call_node.func.attr == "create_guideline":
                                guideline = self._extract_guideline_from_call(call_node)
                                if guideline:
                                    self.guidelines.append(guideline)

    def _extract_guideline_from_call(self, call_node: ast.Call) -> Optional[Guideline]:
        """Extract guideline from create_guideline call"""
        condition = None
        action = None
        tools = []

        for keyword in call_node.keywords:
            if keyword.arg == "condition":
                condition = self._extract_string_value(keyword.value)
            elif keyword.arg == "action":
                action = self._extract_string_value(keyword.value)
            elif keyword.arg == "tools":
                if isinstance(keyword.value, ast.List):
                    tools = [self._extract_name(t) for t in keyword.value.elts]

        if condition and action:
            return Guideline(condition=condition, action=action, tools=tools)

        return None

    def _extract_string_value(self, node) -> str:
        """Extract string value from AST node, handling dedent and f-strings"""
        if isinstance(node, ast.Constant):
            return str(node.value).strip()
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s.strip()
        elif isinstance(node, ast.Call):
            # Handle dedent() calls
            if isinstance(node.func, ast.Name) and node.func.id == "dedent":
                if node.args:
                    return self._extract_string_value(node.args[0])

        # Fallback: try to evaluate
        try:
            return str(ast.literal_eval(node)).strip()
        except:
            return ""

    def _extract_name(self, node) -> str:
        """Extract name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        return ""

    def _find_comment_for_line(self, lineno: int) -> Optional[str]:
        """Find comment on the line before given line number"""
        lines = self.source_code.split('\n')

        # Check line before
        if lineno > 1:
            prev_line = lines[lineno - 2].strip()
            if prev_line.startswith('#'):
                # Remove '# ' prefix and extract comment
                comment = prev_line[1:].strip()
                # Remove "State tX:" prefix if present
                if comment.startswith("State"):
                    comment = comment.split(":", 1)[-1].strip()
                return comment

        return None
