
import os
import json


def get_company_info():
    """
    Fetches the company's knowledge base by reading a local markdown file.
    Use this to answer any questions about the company, its products, policies, history,
    contact information, or recent news.
    """
    try:
        # This path is constructed relative to the current file's location,
        # making it robust and independent of where the server is run from.
        # __file__ -> /.../tool_server/tools/knowledge.py
        # os.path.dirname(__file__) -> /.../tool_server/tools
        # os.path.dirname(...) -> /.../tool_server
        # os.path.join(...) -> /.../tool_server/knowledge/company_info.md
        knowledge_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'knowledge', 'company_info.md'
        )

        with open(knowledge_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Return the content in a structured JSON format, consistent with other tools.
        return json.dumps({
            "status": "success",
            "message": "Company knowledge base retrieved successfully.",
            "content": content
        })
    except FileNotFoundError:
        return json.dumps({
            "status": "error",
            "message": "The company knowledge file (company_info.md) could not be found on the server."
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"An unexpected error occurred while reading the knowledge file: {str(e)}"
        })

