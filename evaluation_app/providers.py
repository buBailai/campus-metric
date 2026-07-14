"""OpenAI 兼容大模型厂商预设，与 OpenMentor/Any2Manim 配置习惯一致。"""

PROVIDERS = {
    'deepseek': {'label': 'DeepSeek', 'base_url': 'https://api.deepseek.com/v1', 'model': 'deepseek-chat', 'needs_key': True},
    'doubao': {'label': '豆包 / 火山方舟', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3', 'model': '', 'needs_key': True},
    'qwen': {'label': '阿里通义千问', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model': 'qwen-plus', 'needs_key': True},
    'glm': {'label': '智谱 GLM', 'base_url': 'https://open.bigmodel.cn/api/paas/v4', 'model': 'glm-4-plus', 'needs_key': True},
    'siliconflow': {'label': '硅基流动', 'base_url': 'https://api.siliconflow.cn/v1', 'model': 'Qwen/Qwen2.5-72B-Instruct', 'needs_key': True},
    'moonshot': {'label': '月之暗面 Kimi', 'base_url': 'https://api.moonshot.cn/v1', 'model': 'moonshot-v1-32k', 'needs_key': True},
    'openai': {'label': 'OpenAI', 'base_url': 'https://api.openai.com/v1', 'model': 'gpt-4o-mini', 'needs_key': True},
    'cherry': {'label': 'Cherry Studio 企业网关', 'base_url': 'https://express-ent-admin.cherryin.ai/v1', 'model': 'deepseek/deepseek-v4-flash', 'needs_key': True},
    'ollama': {'label': 'Ollama 本地', 'base_url': 'http://localhost:11434/v1', 'model': 'qwen2.5', 'needs_key': False},
    'custom': {'label': '自定义 OpenAI 兼容', 'base_url': '', 'model': '', 'needs_key': True},
}


def provider_list():
    return [{'key': key, **value} for key, value in PROVIDERS.items()]


def needs_api_key(provider):
    return PROVIDERS.get(provider, PROVIDERS['custom'])['needs_key']
