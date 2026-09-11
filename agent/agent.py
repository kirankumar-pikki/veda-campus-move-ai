# import json
# import os
# from openai import OpenAI
# from .prompts import SYSTEM_PROMPT
# from .tools import TOOLS, TOOL_SCHEMAS

# class CampusTransportAgent:
#     def __init__(self):
#         api_key = os.getenv("OPENAI_API_KEY", "").strip()

#     # Treat the placeholder as "no API key"
#         if not api_key or api_key == "your_api_key_here":
#             api_key = None

#         self.model = os.getenv("OPENAI_MODEL", "gpt-5.6")

#         self.client = (
#             OpenAI(api_key=api_key, timeout=30.0)
#             if api_key
#             else None
#     )

#     def run(self, user_message: str) -> dict:
#         if not self.client:
#             return self._demo_fallback(user_message)

#         response = self.client.responses.create(
#             model=self.model,
#             instructions=SYSTEM_PROMPT,
#             input=user_message,
#             tools=TOOL_SCHEMAS,
#             tool_choice="auto",
#             max_output_tokens=900,
#         )

#         tool_log = []
#         for _ in range(6):
#             calls = [item for item in response.output if item.type == "function_call"]
#             if not calls:
#                 return {
#                     "answer": response.output_text,
#                     "tools_used": tool_log,
#                     "mode": "live-agent"
#                 }

#             tool_outputs = []
#             for call in calls:
#                 name = call.name
#                 args = json.loads(call.arguments or "{}")
#                 if name not in TOOLS:
#                     result = {"error": f"Unknown tool: {name}"}
#                 else:
#                     try:
#                         result = TOOLS[name](**args)
#                     except Exception as exc:
#                         result = {"error": f"Tool failed: {str(exc)}"}

#                 tool_log.append(name)
#                 tool_outputs.append({
#                     "type": "function_call_output",
#                     "call_id": call.call_id,
#                     "output": json.dumps(result, ensure_ascii=False),
#                 })

#             response = self.client.responses.create(
#                 model=self.model,
#                 instructions=SYSTEM_PROMPT,
#                 input=response.output + tool_outputs,
#                 tools=TOOL_SCHEMAS,
#                 tool_choice="auto",
#                 max_output_tokens=900,
#             )

#         return {
#             "answer": "I could not safely finish the multi-step transport analysis within the tool-call limit.",
#             "tools_used": tool_log,
#             "mode": "live-agent"
#         }

#     def _demo_fallback(self, message: str) -> dict:
#         """Keeps the UI usable without an API key; this is deterministic tool-backed demo mode."""
#         text = message.lower()
#         if "waiting" in text or "students" in text or "overcrowd" in text:
#             data = TOOLS["analyze_demand"]()
#             return {
#                 "answer": self._format_demo_analysis(data),
#                 "tools_used": ["analyze_demand"],
#                 "mode": "demo-no-api-key"
#             }

#         fleet = TOOLS["get_fleet_status"]()["buses"]
#         if "bus" in text or "running" in text or "seat" in text or "route" in text:
#             running = [b for b in fleet if b["status"] in ("running", "delayed")]
#             running.sort(key=lambda x: x["eta_minutes"])
#             best = running[0]
#             return {
#                 "answer": (
#                     f"Demo live-data result: {len(running)} buses are currently active. "
#                     f"The quickest active bus in this snapshot is {best['bus_id']} on {best['route_name']}, "
#                     f"ETA {best['eta_minutes']} min, with {best['available_seats']} seats available. "
#                     "Add OPENAI_API_KEY to enable natural-language multi-step agent reasoning."
#                 ),
#                 "tools_used": ["get_fleet_status"],
#                 "mode": "demo-no-api-key"
#             }

#         return {
#             "answer": (
#                 "I can answer campus transport questions using the local live-demo dataset. "
#                 "Try asking about running buses, seats, delays, traffic, waiting students, "
#                 "alternative buses, maintenance, or bus redistribution. "
#                 "For full AI-agent reasoning, add OPENAI_API_KEY to .env."
#             ),
#             "tools_used": [],
#             "mode": "demo-no-api-key"
#         }

#     @staticmethod
#     def _format_demo_analysis(data):
#         routes = data["routes"]
#         ranked = sorted(routes.items(), key=lambda x: x[1]["pressure"], reverse=True)
#         top = ranked[0]
#         return (
#             f"Highest current demand pressure is {top[0]} ({top[1]['route']}) with "
#             f"{top[1]['waiting_students']} waiting students and {top[1]['available_seats']} available seats. "
#             f"Pressure ratio: {top[1]['pressure']}. "
#             "Use the full AI mode for a multi-step recommendation combining demand, fleet, incidents and route conditions."
#         )
import json
import os

from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .tools import TOOLS, TOOL_SCHEMAS


class CampusTransportAgent:

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()

        if not api_key or api_key == "your_api_key_here":
            api_key = None

        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6")

        self.client = (
            OpenAI(
                api_key=api_key,
                timeout=30.0,
            )
            if api_key
            else None
        )

    def run(self, user_message: str) -> dict:

        # No API key → use local agent
        if not self.client:
            return self._demo_fallback(user_message)

        try:
            return self._run_openai_agent(user_message)

        except Exception as exc:
            error_text = str(exc).lower()

            # OpenAI quota / credits exhausted
            if (
                "credit_balance_exhausted" in error_text
                or "insufficient_quota" in error_text
                or "429" in error_text
                or "rate limit" in error_text
            ):
                fallback = self._demo_fallback(user_message)

                fallback["mode"] = "local-fallback"
                fallback["answer"] = (
                    "⚠️ OpenAI AI reasoning is currently unavailable "
                    "because the API account has no remaining credits.\n\n"
                    + fallback["answer"]
                    + "\n\n"
                    "The CampusMove local transport engine was used instead."
                )

                return fallback

            # Network / timeout problems
            if (
                "timeout" in error_text
                or "connecterror" in error_text
                or "connection" in error_text
            ):
                fallback = self._demo_fallback(user_message)

                fallback["mode"] = "local-fallback"
                fallback["answer"] = (
                    "⚠️ The AI service could not be reached.\n\n"
                    + fallback["answer"]
                    + "\n\n"
                    "The CampusMove local transport engine was used instead."
                )

                return fallback

            # Unknown error → still try local engine
            fallback = self._demo_fallback(user_message)

            fallback["mode"] = "local-fallback"
            fallback["answer"] = (
                "⚠️ AI reasoning failed, so CampusMove switched "
                "to its local transport engine.\n\n"
                + fallback["answer"]
            )

            return fallback

    def _run_openai_agent(self, user_message: str) -> dict:

        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=user_message,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            max_output_tokens=900,
        )

        tool_log = []

        for _ in range(6):

            calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]

            if not calls:
                return {
                    "answer": response.output_text,
                    "tools_used": tool_log,
                    "mode": "live-agent",
                }

            tool_outputs = []

            for call in calls:

                name = call.name

                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if name not in TOOLS:
                    result = {
                        "error": f"Unknown tool: {name}"
                    }

                else:
                    try:
                        result = TOOLS[name](**args)

                    except Exception as exc:
                        result = {
                            "error": f"Tool failed: {str(exc)}"
                        }

                tool_log.append(name)

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                })

            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=response.output + tool_outputs,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                max_output_tokens=900,
            )

        return {
            "answer": (
                "I could not safely finish the multi-step "
                "transport analysis."
            ),
            "tools_used": tool_log,
            "mode": "live-agent",
        }

    def _demo_fallback(self, message: str) -> dict:

        text = message.lower()

        # Demand / overcrowding questions
        if (
            "waiting" in text
            or "students" in text
            or "overcrowd" in text
            or "demand" in text
            or "capacity" in text
        ):

            data = TOOLS["analyze_demand"]()

            return {
                "answer": self._format_demo_analysis(data),
                "tools_used": ["analyze_demand"],
                "mode": "demo-no-api-key",
            }

        # Bus / route questions
        fleet_data = TOOLS["get_fleet_status"]()
        fleet = fleet_data["buses"]

        if (
            "bus" in text
            or "running" in text
            or "seat" in text
            or "route" in text
            or "eta" in text
            or "delay" in text
        ):

            running = [
                bus
                for bus in fleet
                if bus["status"] in ("running", "delayed")
            ]

            if not running:
                return {
                    "answer": (
                        "There are currently no active buses "
                        "in the transport snapshot."
                    ),
                    "tools_used": ["get_fleet_status"],
                    "mode": "demo-no-api-key",
                }

            running.sort(
                key=lambda bus: bus["eta_minutes"]
            )

            best = running[0]

            return {
                "answer": (
                    f"CampusMove live-data result: "
                    f"{len(running)} buses are currently active.\n\n"
                    f"🚍 Best current option: {best['bus_id']}\n"
                    f"Route: {best['route_name']}\n"
                    f"ETA: {best['eta_minutes']} minutes\n"
                    f"Available seats: {best['available_seats']}\n"
                    f"Status: {best['status']}\n\n"
                    "This result is generated from the CampusMove "
                    "transport data engine."
                ),
                "tools_used": ["get_fleet_status"],
                "mode": "demo-no-api-key",
            }

        return {
            "answer": (
                "I can help with CampusMove transport operations.\n\n"
                "Try asking:\n"
                "• Which buses are running right now?\n"
                "• Which bus has the most seats?\n"
                "• Which buses are delayed?\n"
                "• Where are students waiting?\n"
                "• Which route needs another bus?\n"
                "• What should we do if BUS-302 breaks down?"
            ),
            "tools_used": [],
            "mode": "demo-no-api-key",
        }

    def _format_demo_analysis(self, data: dict) -> str:

        if not data:
            return "No demand analysis is currently available."

        # Handle the existing tool's output safely
        if isinstance(data, dict):

            if "summary" in data:
                return str(data["summary"])

            if "analysis" in data:
                return str(data["analysis"])

            if "routes" in data:

                lines = [
                    "CampusMove demand analysis:"
                ]

                for route in data["routes"]:
                    lines.append(
                        f"- {route}"
                    )

                return "\n".join(lines)

        return str(data)