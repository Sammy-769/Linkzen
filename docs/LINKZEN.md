# Linkzen — How and Why I Built It

## It started with LinkedIn

I wanted to grow my LinkedIn account.

I was learning about AWS, cloud engineering, AI and other things, and I wanted to share what I was learning with people on LinkedIn.

Because it is the AI era, I naturally started using ChatGPT to help me write posts.

It worked, but there was a problem.

The posts often sounded like AI had written them.

And the bigger problem wasn't really the writing.

I started thinking about what it actually means to let AI manage your LinkedIn.

If an AI writes your posts, talks to your connections and decides what you should say, while you don't really know your own audience or understand why you are doing those things, are you actually growing your LinkedIn?

I didn't think so.

I wanted AI to **help me grow**, not to **grow instead of me**.

## Then I had an idea

I was also watching YouTube videos from professional LinkedIn creators and learning how they approach LinkedIn.

They had a lot of useful advice about things such as writing posts, creating hooks, understanding content and building a presence.

I started thinking:

**What if I could collect all of this knowledge somewhere and have an AI help me use it when I need it?**

That sounded much more useful to me than simply asking an AI to write another post.

So I thought:

**Why don't I build my own AI?**

And that became Linkzen.

## The idea behind Linkzen

The main idea was simple:

I wanted an AI assistant that knew the knowledge I had collected, understood my preferences and could help me with LinkedIn — without taking over my account or my relationships.

This is where RAG became important.

Instead of putting all my knowledge into every conversation, Linkzen stores the information and retrieves the parts that are relevant to what I am asking.

For example, if I ask Linkzen for help with a LinkedIn post, it can search the knowledge I have collected and bring the relevant information into the conversation.

That means I can keep adding useful material instead of starting from zero every time.

## Why RAG?

I chose RAG because I didn't want Linkzen to depend only on what the language model already knew.

I wanted to be able to say:

> "This is something I learnt from a LinkedIn creator. Keep it with the rest of my knowledge and help me use it later."

The knowledge is processed into smaller pieces and converted into embeddings. Linkzen uses those embeddings to find information that is relevant to a question.

I used **Sentence Transformers with `all-MiniLM-L6-v2`** for the embeddings and **ChromaDB** to store and search them.

The basic process looks like this:

```text
My knowledge
     ↓
Clean and split into pieces
     ↓
Create embeddings
     ↓
Store in ChromaDB
     ↓
I ask Linkzen something
     ↓
Find relevant knowledge
     ↓
Give that context to the AI
     ↓
Generate the answer
```

I also built the indexing system so that Linkzen can recognise when knowledge has changed instead of unnecessarily processing everything again.

## Choosing the AI model

Then came another question:

**Which AI model should actually power Linkzen?**

I looked at different options and compared what they could do, how much they cost and whether they made sense for a personal project.

I didn't need the most expensive model available.

I needed a model that was capable enough for writing, analysing content and working with the context retrieved by my RAG system, while keeping the cost reasonable.

I eventually chose **DeepSeek** because the pricing made sense for what I wanted to build.

That was important because Linkzen is my own project. I wanted to be able to actually use it without worrying that every experiment was going to become expensive.

## Giving Linkzen memory

RAG solved one problem: giving Linkzen access to my stored knowledge.

But there was another problem.

I didn't want to explain myself again and again.

So I built a memory system as well.

Linkzen can keep useful information about the user and use relevant memories when answering.

This is different from the knowledge base.

The knowledge base is more like:

> "Here is information I have collected."

Memory is more like:

> "Here is information about me that can help Linkzen work with me."

Keeping these separate made more sense for the way I wanted to use the system.

## Building the LinkedIn side

Once the RAG and memory systems were working, I started building the actual LinkedIn tools around them.

Linkzen can help with different parts of the LinkedIn workflow, including:

- Analysing a profile
- Creating posts
- Analysing posts
- Coming up with post ideas
- Writing comments
- Replying to messages
- Asking questions about my stored knowledge

The important part is that these tools can use the context available to Linkzen instead of treating every request as a completely new conversation.

## I didn't want to build another chatbot

One thing I kept in mind while building Linkzen was that I didn't want it to become another general-purpose chatbot.

There are already plenty of those.

The point of Linkzen was to build something around **my own workflow**.

I wanted to learn about LinkedIn while using it.

I wanted to collect useful knowledge.

I wanted to interact with my own connections.

And I wanted AI to help me make better decisions and create better content without pretending that the AI was the one building my relationships.

That distinction is probably the most important part of the project.

## What I ended up building

Linkzen is a local AI application with a web interface and a Python backend.

The main parts work roughly like this:

```text
                    Linkzen
                       │
                       ▼
                 Web Interface
                       │
                       ▼
                    FastAPI
                       │
                       ▼
                  AI Assistant
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Memory         RAG       Web Reading
          │            │
          ▼            ▼
     User context   ChromaDB
                       │
                       ▼
                  Embeddings
                       │
                       ▼
                  DeepSeek API
```

The different parts each have a job.

**FastAPI** handles the application and communication between the interface and the backend.

**RAG and ChromaDB** handle the knowledge I have collected.

**Embeddings** help Linkzen find the information that is relevant to a question.

**Memory** keeps useful information about the user.

**DeepSeek** is responsible for understanding the context and generating the final response.

There are also supporting parts for things such as web reading, images, settings, usage tracking and testing.

## The challenges

Building it wasn't as simple as putting an API key into a Python script.

I had to deal with things such as retrieving the right information, keeping the context under control, making the memory useful, handling different LinkedIn tasks and making sure the system didn't simply produce generic AI answers.

There were also plenty of moments where something worked once and then mysteriously stopped working.

That was probably one of the more useful parts of building it.

Instead of just learning how to call an AI API, I started learning how an actual AI application needs to be put together.

I learned about embeddings, vector search, RAG, prompt design, APIs, memory, testing and how different parts of an application affect each other.

## Where Linkzen is now

Linkzen is now a completed working project.

It does what I originally wanted it to do: give me an AI assistant that can work with my own knowledge and context while keeping **me** in control of my LinkedIn.

I may add more features and improvements in the future, but the original idea is already there.

It started with a simple problem:

**I wanted to grow my LinkedIn, but I didn't want AI to grow it for me.**

So instead of paying for another LinkedIn AI and handing over the work, I decided to build one for myself.

And that idea became Linkzen.
