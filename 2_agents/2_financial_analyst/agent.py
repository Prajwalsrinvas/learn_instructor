import inspect
import json
import os
import uuid
from typing import Callable, Type

import instructor
from colorama import Fore, Style
from openai import OpenAI
from pydantic import BaseModel, Field, create_model
from rich import print_json


class Agent:
    class BasicResponse(BaseModel):
        response: str
        rationale: str

    def __init__(self, name: str, openai_client: OpenAI):
        self.name = name
        self.brain = instructor.from_openai(openai_client)
        self.memory = []
        self.tools = {}
        self.session_id = str(uuid.uuid4())
        self.session_folder = os.path.join("sessions", self.session_id)
        os.makedirs(self.session_folder, exist_ok=True)
        print(f"{Fore.GREEN}Session ID: {self.session_id}{Style.RESET_ALL}")
        self.completions = []
        self.total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def _save_memory(self):
        with open(os.path.join(self.session_folder, "agent_memory.json"), "w") as f:
            json.dump(self.memory, f, indent=2)

    def remember(self, memory: str):
        self.memory.append(memory)
        self._save_memory()

    def add_tool(self, tool: Callable):
        self.tools[tool.__name__] = tool

    def tools_list(self):
        return ",".join(self.tools.keys())

    def get_tool(self, tool_name: str):
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self.tools[tool_name]

    def _get_system_message(self):
        return f"""
            You are a helpful assistant named {self.name}
            You are here to help the user with their queries
            Your internal knowledge base might be outdated, so you should rely on the internet for the most recent information
            Your knowledge cutoff is 2022 so for anything beyond you have to search the internet
            You can use the following tools: {self.tools_list()}
            You present your answers in well formatted markdown
        """

    def _save_completion(self, completion):
        completion_dump = completion.model_dump()
        self.completions.append(completion_dump)
        with open(os.path.join(self.session_folder, "completions.json"), "w") as f:
            json.dump(self.completions, f, indent=2)

    def _update_usage(self, usage):
        self.total_usage["prompt_tokens"] += usage.prompt_tokens
        self.total_usage["completion_tokens"] += usage.completion_tokens
        self.total_usage["total_tokens"] += usage.total_tokens

    def use_brain(self, prompt: str, response_model: Type[BaseModel]):
        print(f"\n{Fore.YELLOW}🧠 Thinking...{Style.RESET_ALL}")
        OPENAI_MODEL = "gpt-4o-mini"
        output, completion = self.brain.chat.completions.create_with_completion(
            model=OPENAI_MODEL,
            response_model=response_model,
            messages=[
                {"role": "system", "content": self._get_system_message()},
                {"role": "user", "content": prompt},
            ],
        )
        self._save_completion(completion)
        self._update_usage(completion.usage)
        return output

    def use_tool(self, tool_name: str, *args, **kwargs):
        print(f"{Fore.CYAN}🔧 Using tool: {tool_name}{Style.RESET_ALL}")
        return self.get_tool(tool_name)(*args, **kwargs)

    def get_tool_signature(self, tool: Callable) -> dict:
        signature = inspect.signature(tool)
        return {
            param.name: (param.annotation, ...)
            for param in signature.parameters.values()
            if param.name != "self"
            and param.kind in [param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY]
        }

    def generate_pydantic_model_for_tool(
        self, tool: Callable, model_name: str = "DynamicToolModel"
    ) -> Type[BaseModel]:
        fields = self.get_tool_signature(tool)
        return create_model(model_name, **fields)

    def _generate_plan(self, directive: str):
        class Step(BaseModel):
            step: str
            tool: str = Field(
                default="",
                description=f"The tool to use, can be empty if no need for a tool. The tool should be one of {self.tools_list()}",
            )
            rationale: str

        class Plan(BaseModel):
            steps: list[Step]

        print(f"{Fore.GREEN}📝 Generating plan...{Style.RESET_ALL}")
        return self.use_brain(directive, Plan)

    def _execute_tool_step(self, step, directive: str):
        print(f"{Fore.BLUE}🛠️ Executing tool step: {step.tool}{Style.RESET_ALL}")
        tool_model = self.generate_pydantic_model_for_tool(self.get_tool(step.tool))
        arguments = self.use_brain(
            f"Generate arguments for '{step.tool}' based on '{step.step}' and '{step.rationale}' to achieve '{directive}'",
            tool_model,
        )
        tool_output = self.use_tool(step.tool, **arguments.model_dump())
        print(f"{Fore.MAGENTA}📊 Tool output:{Style.RESET_ALL}")

        if step.tool in ("get_company_news", "get_company_name_and_ticker"):
            print_json(data=tool_output)
        else:
            print(tool_output)
        self.remember(f"'{step.step}' - '{step.rationale}' - '{tool_output}'")

    def _execute_brain_step(self, step, directive: str):
        print(f"{Fore.YELLOW}💡 Executing brain step{Style.RESET_ALL}")
        output = self.use_brain(
            f"Do {step.step} based on {step.rationale} to achieve {directive}",
            self.BasicResponse,
        )
        print(f"{Fore.WHITE}Response: {output.response}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLUE_EX}Rationale: {output.rationale}{Style.RESET_ALL}")
        self.remember(f"{step.step} - {step.rationale} - {output}")

    def _execute_plan(self, plan, directive: str):
        for i, step in enumerate(plan.steps, 1):
            print(f"{Fore.GREEN}📌 Step {i}: {step.step}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💭 Rationale: {step.rationale}{Style.RESET_ALL}")

            if step.tool:
                self._execute_tool_step(step, directive)
            else:
                self._execute_brain_step(step, directive)

    def _generate_conclusion(self, directive: str):
        recent_memory = " ".join(self.memory[-len(self.memory) :])

        class Conclusion(BaseModel):
            conclusion: str
            continue_agent: bool

        print(f"{Fore.GREEN}🏁 Generating conclusion...{Style.RESET_ALL}")
        conclusion = self.use_brain(
            f"Generate a conclusion based on directive {directive} and responses gathered after taking some steps {recent_memory}. If the conclusion is satisfactory, stop the agent.",
            Conclusion,
        )

        print(f"{Fore.YELLOW}📊 Conclusion: {conclusion.conclusion}{Style.RESET_ALL}")

        if conclusion.continue_agent:
            print(f"{Fore.MAGENTA}🔄 Continuing agent execution...{Style.RESET_ALL}")
            self.run(conclusion.conclusion)
        else:
            print(f"{Fore.GREEN}✅ Agent execution completed.{Style.RESET_ALL}")

    def _print_total_usage(self):
        print(f"\n{Fore.CYAN}📊 Total Usage:{Style.RESET_ALL}")
        print(f"  Prompt Tokens: {self.total_usage['prompt_tokens']}")
        print(f"  Completion Tokens: {self.total_usage['completion_tokens']}")
        print(f"  Total Tokens: {self.total_usage['total_tokens']}")

    def run(self, directive: str):
        print(
            f"{Fore.MAGENTA}🤖 {self.name} is running with the directive: {directive}{Style.RESET_ALL}"
        )
        plan = self._generate_plan(directive)
        self._execute_plan(plan, directive)
        self._generate_conclusion(directive)
        self._save_memory()
        self._print_total_usage()
