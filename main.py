import os, time, json, dotenv
from openai import OpenAI
from tools_browser import TOOL_SCHEMAS, TOOL_MAP, browser_goto  # import helpers

dotenv.load_dotenv()
client = OpenAI()

SYSTEM_PROMPT = open("prompt.txt", encoding="utf-8").read()

assistant = client.beta.assistants.create(
    name        = "Pipeline Pilot",
    model       = "gpt-4.1-nano",
    instructions= SYSTEM_PROMPT,
    tools       = TOOL_SCHEMAS,
)

def run():
    thread = client.beta.threads.create()
    print("🟢 Pipeline Pilot ready — log into HubSpot in the browser, then ask questions.")
    while True:
        user = input("🧑 > ").strip()
        if user.lower() in {"quit", "exit", "q"}:
            break
        if not user:
            continue

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        # --- long‑poll loop ---
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "requires_action":
                outputs = []
                for tc in run_status.required_action.submit_tool_outputs.tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments
                    if raw_args:
                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            # Guard against malformed JSON from tool call
                            args = {}
                    else:
                        args = {}
                    if fn_name not in TOOL_MAP:
                        # Unknown or internal tool
                        outputs.append({"tool_call_id": tc.id, "output": "Tool not exposed"})
                        continue
                    try:
                        result = TOOL_MAP[fn_name](**args)
                    except Exception as e:
                        result = f"Tool error: {e}"
                    outputs.append({"tool_call_id": tc.id, "output": result})
                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=outputs
                )
            elif run_status.status in {"completed", "failed", "cancelled"}:
                break
            else:
                time.sleep(0.4)

        # print assistant reply
        msg = client.beta.threads.messages.list(
            thread_id=thread.id,
            order="desc",
            limit=1
        ).data[0]
        if msg.role == "assistant":
            print("🤖", msg.content[0].text.value)

if __name__ == "__main__":
    browser_goto("https://app.hubspot.com/login")
    input("🔑  Log into HubSpot, then press <Enter> here to continue… ")
    run()