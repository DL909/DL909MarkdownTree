#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_client.py - LLM interaction client for novelWriter
"""

import os
import time
from pathlib import Path
import logging

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageFunctionToolCallParam,
)
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
    FunctionCall,
)
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.completion_create_params import ResponseFormat
from openai.types.chat.chat_completion_tool_message_param import (
    ChatCompletionToolMessageParam,
)
from typing import Callable, Iterable, Sequence, TypeVar
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
import json
from typing import Any
from pydantic import BaseModel

from dl909agentframework.llm.tools.permissions import Permission
from dl909agentframework.tree_doc.node import Node
from dl909agentframework.tree_doc.protocols import AttributedMarkdownTextFileProtocol
from dl909agentframework.llm.tools.registry import Tool, ToolRegistry
from dl909agentframework.llm.tools.context import ToolContext
from dl909agentframework.llm.tools.markdown_edit_tools import (
    create_markdown_edit_tools_registry,
)
from dl909agentframework.llm.tools.registry import default_must_use_check

logger = logging.getLogger(__name__)


class ToolLoopLimitError(Exception):
    """工具调用循环达到最大迭代次数上限时抛出"""


def _create_openai_client() -> OpenAI:
    """创建 OpenAI 客户端实例"""
    return OpenAI(
        api_key=str(os.getenv("LLM_API_KEY")),
        base_url=str(os.getenv("LLM_API_BASE")),
    )


def _create_extra_body(enable_thinking: bool) -> dict:
    """创建 API 调用的 extra_body 参数"""
    extra_body = {}
    if enable_thinking:
        extra_body["enable_thinking"] = True
    return extra_body


def _get_temperature(temperature: float | None) -> float:
    """获取 temperature 值，如果未提供则从环境变量读取"""
    if temperature is not None:
        return temperature
    return float(os.getenv("LLM_TEMPERATURE", 0.8))


def _call_llm_api(
    client: OpenAI,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    temperature: float,
    response_format: ResponseFormat = {"type": "text"},
    extra_body: dict | None = None,
    parallel_tool_calls: bool = False,
    tools: list | None = None,
) -> ChatCompletion:
    """执行 LLM API 调用"""
    start_time = time.time()

    create_params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": response_format,
    }

    if extra_body:
        create_params["extra_body"] = extra_body

    if tools:
        create_params["tools"] = tools

    if parallel_tool_calls:
        create_params["parallel_tool_calls"] = parallel_tool_calls

    response = client.chat.completions.create(**create_params)

    elapsed_time = time.time() - start_time
    logger.info("LLM API call completed in %.2f seconds", elapsed_time)

    return response


def _process_tool_call(
    tool_call: Any,
    context: ToolContext,
    registry: ToolRegistry,
) -> tuple[ChatCompletionToolMessageParam, bool]:
    """处理单个工具调用

    Args:
        tool_call: OpenAI tool_call 对象
        context: 工具执行上下文
        registry: 工具注册表

    Returns:
        tool_message 字典
        bool 应当终止工具调用循环
    """
    tool_call_id = tool_call.id
    func_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    logger.info("Tool call: %s(args=%s)", func_name, arguments)

    tool_result, success, should_end_loop = registry.execute(
        func_name, context, arguments
    )

    if not success:
        logger.warning("Tool call failed: %s", tool_result)
    else:
        logger.info(
            "Tool call succeeded: %s",
            tool_result[:100] if len(tool_result) > 100 else tool_result,
        )

    return (
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_result,
        },
        should_end_loop,
    )


def call_llm(
    system_content: str,
    user_content: str,
    call_llm_information_file: Path | None = None,
    response_format: ResponseFormat = {"type": "text"},
    enable_thinking: bool = True,
    temperature: float | None = None,
) -> str:
    """
    调用 LLM API 获取响应

    Args:
        system_prompt: 系统提示词
        user_content: 用户输入内容
        call_llm_information_file_name: 可选，保存调用信息的文件名
        response_format: 决定返回格式，默认设置为文本。
        enable_thinking: 使用思考模式，需要模型支持
        use_cache: 在缓存中有system_content和user_content一致的内容时使用缓存
        temperature: 设置时，覆写.env设置的temperature

    Returns:
        LLM 响应的文本内容
    """

    logger.debug(
        "LLM request params: model=%s, temperature=%s, enable_thinking=%s",
        os.getenv("LLM_MODEL"),
        temperature,
        enable_thinking,
    )
    logger.debug("System content: %s", system_content)
    logger.debug("User content: %s", user_content)

    # 初始化 OpenAI 客户端
    client = _create_openai_client()
    extra_body = _create_extra_body(enable_thinking)
    temperature = _get_temperature(temperature)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # 调用 API
    response = _call_llm_api(
        client=client,
        model=str(os.getenv("LLM_MODEL")),
        messages=messages,
        temperature=temperature,
        response_format=response_format,
        extra_body=extra_body,
    )

    output = response.choices[0].message
    assistant_message: dict = {
        "role": "assistant",
        "content": output.content,
    }
    if output.tool_calls:
        assistant_message["tool_calls"] = output.tool_calls
    # reasoning_content 是部分模型（如带思考模式的）返回的非标准扩展字段，
    # 标准 OpenAI 响应上并不存在，用 getattr 保护避免 AttributeError。
    reasoning_content = getattr(output, "reasoning_content", None)
    if reasoning_content is not None:
        assistant_message["reasoning_content"] = reasoning_content
    messages.append(assistant_message)  # pyright: ignore[reportArgumentType]

    _try_dump_log_for_tool_call(call_llm_information_file, messages)

    return str(response.choices[0].message.content)


def tool_loop(
    messages: list[ChatCompletionMessageParam],
    registry: ToolRegistry,
    context: ToolContext | None = None,
    call_llm_information_file_name: Path | None = None,
    response_format: ResponseFormat = {"type": "text"},
    enable_thinking: bool = True,
    temperature: float | None = None,
    parallel_tool_calls: bool = False,
    max_tool_iterations: int = 0,
    client: OpenAI | None = None,
    extra_body: dict | None = None,
    check_list: list[Callable[[ToolRegistry, ToolContext], str | None]] | None = None,
) -> list[ChatCompletionMessageParam]:
    """
    调用 LLM API 并使用工具执行

    Args:
        registry: 工具注册表
        context: 工具执行上下文（可选）
        call_llm_information_file_name: 可选，保存调用信息的文件名
        response_format: 响应格式
        enable_thinking: 使用思考模式
        temperature: 温度参数
        max_tool_iterations: 最大工具调用循环次数
        messages: 信息列表
        check_list: 可选，退出前执行的检查函数列表

    Returns:
        LLM 最终响应的文本内容
    """
    logger.info("Starting call_llm_with_tool")

    if context is None:
        context = ToolContext()

    if client is None:
        client = _create_openai_client()
    if extra_body is None:
        extra_body = _create_extra_body(enable_thinking)
    temperature = _get_temperature(temperature)

    logger.info(
        "Calling LLM API with tools (model=%s, temperature=%s)",
        os.getenv("LLM_MODEL"),
        temperature,
    )
    logger.debug(
        "Tools: %s", [t["function"]["name"] for t in registry.to_openai_tools()]
    )

    tool_call_loop_time = 0
    if not max_tool_iterations:
        max_tool_iterations = int(os.getenv("MAX_TOOL_LOOP", 20))
    should_continue: bool = True

    while should_continue and tool_call_loop_time < max_tool_iterations:
        tool_call_loop_time += 1
        logger.info(
            "Tool call iteration %d/%d",
            tool_call_loop_time,
            max_tool_iterations,
        )

        response = _call_llm_api(
            client=client,
            model=str(os.getenv("LLM_MODEL")),
            messages=messages,
            temperature=temperature,
            extra_body=extra_body,
            tools=registry.to_openai_tools(),
            response_format=response_format,
            parallel_tool_calls=parallel_tool_calls,
        )

        output = response.choices[0].message
        assistant_message: dict = {
            "role": "assistant",
            "content": output.content,
        }
        if output.tool_calls:
            assistant_message["tool_calls"] = output.tool_calls
        reasoning_content = getattr(output, "reasoning_content", None)
        if reasoning_content is not None:
            assistant_message["reasoning_content"] = reasoning_content
        refusal = getattr(output, "refusal", None)
        if refusal:
            assistant_message["refusal"] = refusal
        messages.append(assistant_message)  # pyright: ignore[reportArgumentType]

        if (
            tool_call_loop_time > max_tool_iterations / 4 * 3
            or max_tool_iterations - tool_call_loop_time < 5
        ):
            messages.append(
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=f"warning: you are about to reach tool call loop limitation( max {max_tool_iterations} times, {tool_call_loop_time} times used, {max_tool_iterations - tool_call_loop_time} times left ).",
                )
            )

        if not output.tool_calls:
            if check_list:
                for check_func in check_list:
                    result = check_func(registry, context)
                    if result is not None:
                        messages.append(
                            ChatCompletionSystemMessageParam(
                                role="system",
                                content=result,
                            )
                        )
                        break
                else:
                    should_continue = False
            else:
                should_continue = False
            continue

        for tool_call in output.tool_calls:
            message, should_end_loop = _process_tool_call(tool_call, context, registry)
            messages.append(message)
            if should_end_loop:
                should_continue = False

    if tool_call_loop_time >= max_tool_iterations:
        logger.error(
            "LLM tool call loop interrupted: reached max iteration limit (%d)",
            max_tool_iterations,
        )
        raise ToolLoopLimitError(
            f"工具调用循环达到最大迭代次数上限（{max_tool_iterations} 次）"
        )

    _try_dump_log_for_tool_call(call_llm_information_file_name, messages)
    return messages


def _distil_response_from_messages(
    messages: list[ChatCompletionMessageParam],
) -> str:
    t = messages[-1].get("content", None)
    assert isinstance(t, str)
    return t


def call_llm_interactive_with_tool(
    system_content: str,
    registry: ToolRegistry,
    context: ToolContext | None = None,
    response_format: ResponseFormat = {"type": "text"},
    call_llm_information_file: Path | None = None,
    enable_thinking: bool = True,
    temperature: float | None = None,
    max_tool_iterations: int = 0,
    messages: list[ChatCompletionMessageParam] | None = None,
    check_list: list[Callable[[ToolRegistry, ToolContext], str | None]] | None = None,
) -> None:
    """
    交互式命令行对话函数，支持多轮对话和 tool calling

    Args:
        system_content: 系统提示词
        registry: 工具注册表
        context: 工具执行上下文（可选）
        call_llm_information_file: 可选，保存对话历史的路径
        enable_thinking: 使用思考模式
        temperature: 温度参数
        max_tool_iterations: 最大工具调用迭代次数
        check_list: 可选，退出前执行的检查函数列表

    使用方法:
        - 输入 \\q 退出对话
        - 输入 \\n 作为行尾来输入多行内容
    """
    logger.info("Starting interactive chat session with tools")

    if context is None:
        context = ToolContext()

    client = _create_openai_client()

    if messages is None:
        messages = [
            {"role": "system", "content": system_content},
        ]

    if max_tool_iterations == 0:
        max_tool_iterations = int(os.getenv("MAX_TOOL_LOOP", 20))

    print("=" * 50)
    print("交互式对话模式 - 输入 \\q 退出，\\n 换行")
    print("=" * 50)
    user_lines = []
    print("\n【用户输入】(\\q 退出，行尾输入\\n 换行，\\d 删除上一行):")
    end_flag = False

    while True:
        user_lines = []
        while True:
            try:
                line = input()
            except EOFError:
                end_flag = True
                break
            if line == "\\q":
                end_flag = True
                break
            if line == "\\d":
                user_lines = user_lines[:-1]
                continue
            if line.endswith("\\n"):
                user_lines.append(line[:-2])
            else:
                user_lines.append(line)
                break

        if end_flag:
            break

        user_content = "\n".join(user_lines)

        if not user_content:
            print("输入为空，请重新输入")
            continue

        messages.append({"role": "user", "content": user_content})

        messages = tool_loop(
            registry=registry,
            context=context,
            enable_thinking=enable_thinking,
            response_format=response_format,
            temperature=temperature,
            max_tool_iterations=max_tool_iterations,
            messages=messages,
            client=client,
            check_list=check_list,
            parallel_tool_calls=True,
        )

        print(f"AI:{_distil_response_from_messages(messages)}")

    _try_dump_log_for_tool_call(
        call_llm_information_file=call_llm_information_file, messages=messages
    )


def _dump_log_for_call_llm_with_tool(
    call_llm_information_file: Path, messages: Iterable[ChatCompletionMessageParam]
) -> None:
    """保存工具调用的日志信息"""

    _dump_messages_to_file(call_llm_information_file, messages)


def _try_dump_log_for_tool_call(
    call_llm_information_file: Path | None,
    messages: Iterable[ChatCompletionMessageParam],
) -> None:
    if call_llm_information_file is not None:
        _dump_log_for_call_llm_with_tool(call_llm_information_file, messages)


def _dump_messages_to_file(
    file_path: Path, messages: Iterable[ChatCompletionMessageParam]
) -> None:
    """将消息列表保存到文件"""
    logger.info("Saving conversation history to: %s", file_path)
    file_path.parent.mkdir(exist_ok=True, parents=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for msg in messages:
            if isinstance(msg, BaseModel):
                f.write(
                    msg.model_dump_json(
                        indent=2,
                        exclude_unset=True,
                        exclude_none=True,
                    )
                    + "\n"
                )
            elif isinstance(msg, dict):
                msg_copy = msg.copy()
                if "tool_calls" in msg_copy:
                    tool_calls_serializable = []
                    for tc in msg_copy["tool_calls"]:
                        # tool_call 可能是 pydantic 模型（响应对象）或普通 dict（TypedDict）
                        model_dump = getattr(tc, "model_dump", None)
                        if callable(model_dump):
                            tool_calls_serializable.append(model_dump())
                        else:
                            tool_calls_serializable.append(dict(tc))
                    msg_copy["tool_calls"] = tool_calls_serializable
                f.write(json.dumps(msg_copy, indent=2, ensure_ascii=False) + "\n")
    logger.debug("Conversation history saved successfully")


def call_llm_with_edit_single_markdown_file_tool(
    markdown_file_node: AttributedMarkdownTextFileProtocol,
    system_content: str | None = None,
    user_content: str | None = None,
    response_format: ResponseFormat = {"type": "text"},
    call_llm_information_file: Path | None = None,
    enable_thinking: bool = True,
    temperature: float | None = None,
    extra_tools: Sequence[Tool] | None = None,
    registry: ToolRegistry | None = None,
    permissions: Sequence[tuple[Node, Permission]] | None = None,
    extra_check_list: list[Callable[[ToolRegistry, ToolContext], str | None]]
    | None = None,
    override_default_check_list: list[Callable[[ToolRegistry, ToolContext], str | None]]
    | None = None,
) -> list[ChatCompletionMessageParam]:
    """
    调用 LLM API 使用 function calling 修改指定的 markdown 文件

    封装默认 Markdown 编辑工具集 (replace/append/unfold/read) + 可选额外工具

    Args:
        system_content: 系统提示词
        user_content: 用户输入内容
        markdown_file_node: Markdown 文件节点
        call_llm_information_file: 可选，保存调用信息的文件路径
        enable_thinking: 使用思考模式，需要模型支持
        temperature: 设置时，覆写.env 设置的 temperature
        backup_to: 设置时，将在修改前将目标 markdown 文件备份到对应位置
        extra_tools：可选，传入额外工具
        registry：可选，覆写默认工具集
        permissions：可选，设置工具集权限
        extra_check_list：可选，额外检查函数列表
        override_default_check_list：可选，覆盖默认检查函数列表，为 None 时使用默认值
    """
    logger.info("Starting call_llm_with_edit_single_markdown_file_tool")
    logger.debug(
        "Target markdown file: %s",
        # file_path 是具体文件节点类才有的属性，协议未声明，用 getattr 探测。
        getattr(markdown_file_node, "file_path", "unknown"),
    )
    if registry is None:
        registry = create_markdown_edit_tools_registry(permissions=permissions)

    if extra_tools:
        registry.register(*extra_tools)

    context = ToolContext(markdown_file_node=markdown_file_node)

    if override_default_check_list is not None:
        check_list: list[Callable[[ToolRegistry, ToolContext], str | None]] | None = (
            list(override_default_check_list)
        )
    else:
        check_list = [default_must_use_check]
    if extra_check_list:
        check_list.extend(extra_check_list)
    if check_list is not None and len(check_list) == 0:
        check_list = None

    messages: list[ChatCompletionMessageParam] = []

    if system_content is not None:
        messages.append({"role": "system", "content": system_content})
    if user_content is not None:
        messages.append({"role": "user", "content": user_content})

    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_a55d42e3a8dd48ac8a20b968",
                    "type": "function",
                    "function": {
                        "name": "read",
                        "arguments": "{}",
                    },
                }
            ],
        }
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_a55d42e3a8dd48ac8a20b968",
            "content": markdown_file_node.get_text(),
        }
    )

    assert registry
    tool_loop(
        messages=messages,
        registry=registry,
        context=context,
        response_format=response_format,
        call_llm_information_file_name=call_llm_information_file,
        enable_thinking=enable_thinking,
        temperature=temperature,
        check_list=check_list,
    )

    markdown_file_node.save()
    logger.info("Markdown file saved successfully")

    return messages


def call_llm_interactive_with_edit_markdown_tool(
    system_content: str,
    markdown_file_node: AttributedMarkdownTextFileProtocol,
    call_llm_information_file: Path | None = None,
    enable_thinking: bool = True,
    temperature: float | None = None,
    extra_tool_registries: ToolRegistry | None = None,
    default_registry: ToolRegistry | None = None,
    max_tool_iterations: int = 20,
    extra_check_list: list[Callable[[ToolRegistry, ToolContext], str | None]]
    | None = None,
    override_default_check_list: list[Callable[[ToolRegistry, ToolContext], str | None]]
    | None = None,
) -> None:
    """
    交互式命令行对话函数，支持多轮对话、多行输入和 tool calling

    封装默认 Markdown 编辑工具集（如果提供 markdown_file_node）

    Args:
        system_content: 系统提示词
        markdown_file_node: 可选，Markdown 文件节点，用于支持 tool calling
        call_llm_information_file: 可选，保存对话历史的路径
        enable_thinking: 使用思考模式，需要模型支持
        temperature: 设置时，覆写.env 设置的 temperature
        extra_tool_registries: 可选，额外的工具注册表，与默认工具合并使用
        extra_check_list：可选，额外检查函数列表
        override_default_check_list：可选，覆盖默认检查函数列表，为 None 时使用默认值
    """
    if default_registry is None:
        default_registry = create_markdown_edit_tools_registry()
    if extra_tool_registries:
        registry = default_registry.merge(extra_tool_registries)
    else:
        registry = default_registry
    context = ToolContext(markdown_file_node=markdown_file_node)
    if override_default_check_list is not None:
        check_list: list[Callable[[ToolRegistry, ToolContext], str | None]] | None = (
            list(override_default_check_list)
        )
    else:
        check_list = [default_must_use_check]
    if extra_check_list:
        check_list.extend(extra_check_list)
    if check_list is not None and len(check_list) == 0:
        check_list = None

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_content}
    ]

    messages.append(
        ChatCompletionAssistantMessageParam(
            content="",
            role="assistant",
            tool_calls=[
                ChatCompletionMessageFunctionToolCallParam(
                    id="call_a55d42e3a8dd48ac8a20b968",
                    function=FunctionCall(arguments="{}", name="read"),
                    type="function",
                )
            ],
        )
    )
    messages.append(
        ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id="call_a55d42e3a8dd48ac8a20b968",
            content=markdown_file_node.get_text(),
        ),
    )

    call_llm_interactive_with_tool(
        system_content=system_content,
        registry=registry,
        context=context,
        call_llm_information_file=call_llm_information_file,
        enable_thinking=enable_thinking,
        temperature=temperature,
        max_tool_iterations=max_tool_iterations,
        messages=messages,
        check_list=check_list,
    )

    _try_dump_log_for_tool_call(call_llm_information_file, messages)


T = TypeVar("T", bound=BaseModel)


def parse_json_messages(
    messages: list[ChatCompletionMessageParam], model: type[T]
) -> T:
    t = messages[-1].get("content", None)
    assert isinstance(t, str)
    return model.model_validate_json(t)
