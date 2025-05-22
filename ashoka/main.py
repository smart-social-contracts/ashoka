from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQAWithSourcesChain

# System-level instructions
template = """You are an AI governor advising a decentralized digital realm.
You are given a summary of its current situation using GGG (Generalized Global Governance), a standardized format
for representing goals, assets, land, and citizens.

Your job is to generate a policy proposal that improves governance, using clear reasoning and aligning with the realm’s goals.

Context:
{context}

Question: {question}

Only answer with a JSON object like:
{{ "title": "...", "content": "..." }}
"""

custom_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=template
)

qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type_kwargs={"prompt": custom_prompt}
)

query = "What should this realm do to improve citizen participation?"
result = qa_chain.run(query)

print(result)
