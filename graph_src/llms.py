import os
from dotenv import load_dotenv
load_dotenv()

from langchain_openai.chat_models import ChatOpenAI
from langchain.chat_models import init_chat_model

# 限速设置
from langchain_core.rate_limiters import InMemoryRateLimiter
# 配置速率
rate_limiter = InMemoryRateLimiter(
    requests_per_second=5, # 每秒最多5个请求
    check_every_n_seconds=1, # 每60分钟检查一次是否超过速率限制
)

def get_deepseak_model():
    return ChatOpenAI(
        model='deepseek-chat',
        base_url='https://api.deepseek.com/v1',
        api_key=os.getenv('DEEPSEEK_API_KEY')
    )

def get_doubao_model():
    return ChatOpenAI(
        model='doubao-seed-1-6-251015',
        api_key=os.getenv("DOUBAO_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )

def get_kimi_model():
    return ChatOpenAI(
        model='ep-20260206212726-kb4wt',
        api_key=os.getenv("KIMI_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )


def get_doubao_vision():
    return ChatOpenAI(
        model=os.getenv('IMAGE_PARSER_MODEL'),
        api_key=os.getenv("IMAGE_PARSER_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )
def get_mass_kimi_model():
    return ChatOpenAI(
        model=os.getenv('MASS_KIMI_MODEL'),
        api_key=os.getenv("MASS_KIMI_KEY"),
        base_url=os.getenv("MASS_URL")

    )

def get_mass_glm_5_model():
    return ChatOpenAI(
        model=os.getenv('MASS_GLM_5_MODEL'),
        api_key=os.getenv("MASS_KIMI_KEY"),
        base_url=os.getenv("MASS_URL")
    )

def get_mass_glm_4_model():
    return ChatOpenAI(
        model=os.getenv('MASS_GLM_4_MODEL'),
        api_key=os.getenv("MASS_KIMI_KEY"),
        base_url=os.getenv("MASS_URL")
    )


def get_mass_deepseek_model():
    return ChatOpenAI(
        model=os.getenv('MASS_DEEPSEEKV32_MODEL'),
        api_key=os.getenv("MASS_KIMI_KEY"),
        base_url=os.getenv("MASS_URL")

    )



def get_chat_model():
    return init_chat_model(
        model='ep-20260206212726-kb4wt',
        api_key=os.getenv("KIMI_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        model_provider='openai',
        rate_limiter=rate_limiter

    ).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True
    )

if __name__ == '__main__':
    # model = get_deepseak_model()
    # model = get_kimi_model()
    # model = get_mass_glm_model()
    model = get_mass_glm_4_model()
    # model = get_chat_model()
    response = model.invoke('你是谁')
    print(response)
    # 构建对话历史，依次包含系统设定、助手开场白和用户问题
    # messages = [
    #     {"role": "system", "content": "你是技术专家，回答要专业。"},  # 系统角色：设定助手为技术专家
    #     {"role": "assistant", "content": "我准备好了，请问您遇到什么问题？"},  # 助手角色：主动询问用户问题
    #     {"role": "user", "content": "我的电脑会自动重启。"}  # 用户角色：描述电脑故障
    # ]
    #
    # # 调用模型生成回复
    # resp = model.invoke(messages)
    #
    # # 打印模型返回的回复内容
    # print(resp.content)