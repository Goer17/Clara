import os
import random
from pathlib import Path
import subprocess
import yaml, json
from collections import defaultdict
from abc import ABC, abstractmethod
import datetime
from typing import (
    Dict, List, Tuple
)
from agent.retriever import (
    MemoryNode,
    MemoryManager,
    Retriever
)
from utils.general import (
    gpt_4o, tts_hd,
    LLMEngine,
    AMEngine
)
from utils.string import Formatter
from .logger import logger
from shortuuid import uuid

prompts = Path("config") / "prompts" / "feedback.yml"
with open(prompts) as f:
    all_prompts = yaml.safe_load(f)

class Question(ABC):
    def __init__(self,
                 content: str,
                 solution: str,
                 rela_nodes: List[MemoryNode],
                 analysis: str = None,
                 *args, **kwargs
                 ):
        self.content = content
        self.solution = solution
        self.rela_nodes = rela_nodes
        self.analysis = analysis
        self.answer = None
        self.score = 0
    
    @abstractmethod
    def question(self, hint: bool = False) -> str:
        pass
    
    @abstractmethod
    def mark(self,
             answer: str,
             engine: LLMEngine
             ) -> Tuple[float, str, List[Dict[str, str]]]:
        """ Mark the student's answer
        Args:
            answer (str): student's answer

        Returns:
            float: the mark of this answer: 0 ~ 1
            str: analysis
            List[Dict[str, str]]: mistakes the student had, can be empty
        """
        self.answer = answer


class GapFillingQuestion(Question):
    def __init__(self, content, solution, rela_nodes, analysis = None, *args, **kwargs):
        super().__init__(content, solution, rela_nodes, analysis, *args, **kwargs)
    
    def question(self, hint = False) -> str:
        blank = "_" * len(self.solution)
        if hint:
            blank = self.solution[0] + blank[1:]
        q = self.content.replace("$BLANK", blank)

        return q
    
    def mark(self, answer: str, engine = None):
        super().mark(answer, engine)
        self.score = int(answer.lower() == self.solution.lower())
        return int(answer.lower() == self.solution.lower()), "", []


class SentenceMakingQuestion(Question):
    def __init__(self, content, solution, rela_nodes, analysis = None, *args, **kwargs):
        super().__init__(content, solution, rela_nodes, analysis, *args, **kwargs)
    
    def question(self, hint = False):
        return self.content

    def __feedback(self, answer: str, engine: LLMEngine) -> Tuple[List[str], str]:
        sys_prompt, few_shots = all_prompts["SentenceMakingQuestion"]["sys_prompt"], all_prompts["SentenceMakingQuestion"]["few_shots"]
        prompt = (
            f"scenario: {self.content}\n",
            f"answer: {self.solution}\n",
            f"lang: {', '.join(self.analysis)}\n",
            f"student's answer: {answer}\n"
        )
        prompt = f"```txt\n{prompt}```"
        try:
            response = engine.generate(prompt, sys_prompt, few_shots)
            if "RIGHT" in response:
                return [], ""
            response = Formatter.catch_json(response)
            return response["mistakes"], response["polished"]
        except Exception as e:
            logger.error(f"SentenceMakingQuestion.__feedback() : an error ocurred while attempting to generate feedback of student's answer: {answer}", e)
            return [], ""
    
    def mark(self, answer, engine):
        super().mark(answer, engine)
        if len(answer) == 0:
            return 0, self.analysis, []
        mistakes, polished = self.__feedback(answer, engine)
        self.score = max(0, 1 - len(mistakes) / 4)
        feedbacks = [
            {
                "abstract": ", ".join(mistakes),
                "content": f"Polished version: {polished}"
            }
        ]
        
        return self.score, self.analysis, feedbacks
        

class ListeningQuestion(Question):
    def __init__(self, content, solution, rela_nodes, analysis = None, *args, **kwargs):
        super().__init__(content, solution, rela_nodes, analysis, *args, **kwargs)
    
    def question(self, hint = False):
        return "Listen to the sentence and write down what you hear."
    
    def __editing_dist(self, answer: str) -> int:
        sol_len = len(self.solution)
        ans_len = len(answer)
        dp = [[0] * (ans_len + 1) for _ in range(sol_len + 1)]
        ops = [[-1] * (ans_len + 1) for _ in range(sol_len + 1)]
        for i in range(1, sol_len + 1):
            dp[i][0] = i
            ops[i][0] = 1
        for j in range(1, ans_len + 1):
            dp[0][j] = i
            ops[0][j] = 2
        for i in range(1, sol_len + 1):
            for j in range(1, ans_len + 1):
                if self.solution[i - 1] == answer[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    ops[i][j], dp[i][j] = min(
                        enumerate([1 + dp[i - 1][j - 1], 1 + dp[i - 1][j], 1 + dp[i][j - 1]]),
                        key=lambda x: x[1]
                    )
                    # -1 : do nothing
                    # 0 : sub
                    # 1 : add +
                    # 2 : del -
        i, j = sol_len, ans_len
        analysis = answer
        while i > 0 or j > 0:
            if ops[i][j] == -1:
                i, j = i - 1, j - 1
                continue
            if ops[i][j] == 0:
                # sub : a[j - 1] -> s[i - 1]
                analysis = analysis[ : j - 1] + f"<{answer[j - 1]}:{self.solution[i - 1]}>" + analysis[j :]
                i, j = i - 1, j - 1
            elif ops[i][j] == 1:
                # add : a[ : j] + s[i - 1]
                analysis = analysis[ : j] + f"[{self.solution[i - 1]}]" + analysis[j :]
                i, j = i - 1, j
            elif ops[i][j] == 2:
                # del : a[ : j] -> a[ : j - 1]
                analysis = analysis[ : j - 1] + f"({answer[j - 1]})" + analysis[j :]
                i, j = i, j - 1
        self.analysis = analysis
        
        return dp[-1][-1]
    
    def __feedback(self, answer: str, engine: LLMEngine) -> List[Dict[str, str]]:
        sys_prompt, few_shots = all_prompts["ListeningQuestion"]["sys_prompt"], all_prompts["ListeningQuestion"]["few_shots"]
        prompt = (
            f"original: {self.solution}\n"
            f"student: {answer}"
        )
        prompt = f"```txt\n{prompt}\n```"
        responses = engine.generate(
            prompt=prompt,
            sys_prompt=sys_prompt,
            few_shots=few_shots
        )
        if "NO_ERROR" in responses:
            return []
        try:
            responses = Formatter.catch_json(responses)
            feedbacks = []
            for _, feedback in responses.items():
                feedbacks.append(feedback)
            return feedbacks
        except Exception as e:
            logger.error("ListeningQuestion.__feedback() : an error occurred while attempting to generate the feedback of student's answer.", e)
            return []
    
    def mark(self, answer, engine) -> Tuple[int, str, List[Dict[str, str]]]:
        super().mark(answer, engine)
        self.score = 1 - self.__editing_dist(answer) / max(len(self.solution), len(answer))

        return self.score, self.analysis, []


class Quiz:
    def __init__(self):
        self.filepath = None
        self.knowledges: List[MemoryNode] = []
        self.problemset: Dict[str, List[Question]] = defaultdict(list)
        self.description: str = "The is a vocabulary learning task with several questions."
    
    @staticmethod
    def intro(q_type: str):
        if q_type == "GapFillingQuestion":
            return "Gap Filling: Fill in each blank with a word you have just learned."
        if q_type == "ListeningQuestion":
            return "Listening: Listen to the radio and answer the questions."
        if q_type == "SentenceMakingQuestion":
            return "Sentence Making: Use the word you have just learned to create sentences based on each given scenario."
        
        return "Unknown"
    
    def init_cards(self):
        self.cards = [
            {
                "type": "intro",
                "props": {
                    "content": self.description
                }
            }
        ]
        for knowledge in self.knowledges:
            self.cards.append(
                {
                    "type": "learn",
                    "props": {
                        "abstract": knowledge.get_prop("abstract"),
                        "content": knowledge.get_prop("content")
                    }
                }
            )
        part = 0
        for q_type, problems in sorted(self.problemset.items()):
            part += 1
            self.cards.append(
                {
                    "type": "intro",
                    "props": {
                        "part": part,
                        "content": Quiz.intro(q_type)
                    }
                }
            )
            for idx, problem in enumerate(problems):
                self.cards.append(
                    {
                        "type": "question",
                        "props": {
                            "type": q_type,
                            "idx": idx,
                            "question": problem.question(),
                            "hint_question": problem.question(hint=True),
                            "solution": problem.solution
                        }
                    }
                )
    
    def card(self, idx: int) -> Dict[str, str]:
        if idx < len(self.cards):
            return self.cards[idx]
        else:
            return {
                "type": "end",
                "props": {}
            }
    
    def addn(self, node: MemoryNode):
        self.knowledges.append(node)
    
    def addq(self, q: Question):
        self.problemset[type(q).__name__].append(q)
    
    def shell(self, retriever: Retriever):
        def _clear():
            subprocess.run("clear", shell=True)
        _clear()
        for idx, node in enumerate(self.knowledges):
            print(f"{idx + 1}. {node.get_prop('abstract')}")
            print(node.get_prop('content'))
            input("> Press ENTER to continue :")
            _clear()
        for idx, (q_type, q_list) in enumerate(self.problemset.items()):
            print(f"PART {idx + 1} : {q_type}")
            input("> Press ENTER to start :")
            _clear()
            scale, low = 1, 0
            if q_type == "GapFillingQuestion":
                scale, low = 10, 0
            elif q_type == "ListeningQuestion":
                scale, low = 20, 0.7
            elif q_type == "SentenceMakingQuestion":
                scale, low = 20, 0.6
            else:
                continue
            for q in q_list:
                w = q.rela_nodes[0]
                mistake = q.rela_nodes[1] if len(q.rela_nodes) > 1 else None
                print("=" * 30)
                print(q.question(hint=True))
                print("\n")
                if q_type == "ListeningQuestion":
                    voice = random.choice(
                        ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
                    )
                    name = tts_hd.generate(q.solution, voice)
                    for i in range(2):
                        AMEngine.play(name)
                answer = input("> ")
                score, analysis, feedbacks = q.mark(answer, gpt_4o)
                try:
                    if q_type in ["ListeningQuestion", "SentenceMakingQuestion"] and score <= low and len(feedbacks) > 0:
                        mistake_abstract = ", ".join(v["abstract"] for v in feedbacks) if not mistake else mistake.get_prop("mistake")
                        mistake_feedbacks = "\n".join(f"{v['abstract']} : {v['content']}" for v in feedbacks)
                        mistake_content = (
                            f"question: {q.question(hint=True)}\n"
                            f"solution: {q.solution}\n"
                            f"student's answer: {answer}\n"
                            f"feedbacks : {mistake_feedbacks}"
                        )
                        node_profile = {
                            "label": "mistake",
                            "abstract": mistake_abstract,
                            "type": q_type,
                            "content": mistake_content,
                            "familiarity": 0
                        }
                        node = retriever.remember(node_profile, 0)
                        node.create_rela(w, "relative", {})
                except Exception as e:
                    logger.error(f"Quiz.shell() : an error occurred while attempting to generate a mistake node of {w.get_prop('abstract')}", e)
                print(f"\n* score : {score}")
                print(f"solution : {q.solution}")
                if analysis:
                    print(f"* analysis :\n{analysis}")
                input("> Press ENTER to continue :")
                _clear()
                k = max(-5, int(scale * (score - low)))
                for node in q.rela_nodes:
                    familiarity = node.get_prop("familiarity")
                    if familiarity is None:
                        familiarity = 0
                    familiarity += k
                    node.set_prop("familiarity", familiarity)
                    node.update()
                    logger.info(f"Quiz.shell() : updated [familiarity ({k})] {node}")
                    if familiarity >= 100:
                        if node.label == "unfamiliar_word":
                            node.set_label("word")
                            node.update()
                        elif node.label == "mistake":
                            node.destroy()
        print("> This quiz was completed!")
    
    def save(self, path: str | Path = Path("material") / "quiz") -> str:
        quiz_dat = {"description": self.description}
        quiz_dat["Knowledges"] = []
        for node in self.knowledges:
            quiz_dat["Knowledges"].append(node.get_prop("m_id"))
        for question_type in self.problemset:
            quiz_dat[question_type] = []
            for q in self.problemset[question_type]:
                q_dat = {
                    "content": q.content,
                    "solution": q.solution,
                    "rela_nodes": []
                }
                if q.analysis:
                    q_dat["analysis"] = q.analysis
                for rela_node in q.rela_nodes:
                    q_dat["rela_nodes"].append(rela_node.get_prop("m_id"))
                quiz_dat[question_type].append(q_dat)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if not isinstance(path, Path):
            path = Path(path)
        if not os.path.exists(path):
            os.makedirs(path)
        filepath = path / f"[{timestamp} {uuid()[:4]}].json"
        with open(filepath, 'w') as f:
            quiz_dat_str = json.dumps(quiz_dat)
            f.write(quiz_dat_str)
        
        return filepath
    
    @staticmethod
    def load(filepath: str | Path, retriever: Retriever) -> 'Quiz':
        try:
            with open(filepath) as f:
                quiz_dat: Dict = json.load(f)
        except Exception as e:
            logger.error(f"Quiz.load() : an error ocurred while attempting to load a knowledge from quiz {filepath}", e)
            return None
        quiz = Quiz()
        if "description" in quiz_dat:
            quiz.description = quiz_dat["description"]
        knowledges = quiz_dat.pop("Knowledges", [])
        for m_id in knowledges:
            try:
                node = retriever.match_node(
                    {"m_id": m_id}
                )[0]
                quiz.addn(node)
            except Exception as e:
                logger.error(f"Quiz.load() : an error ocurred while attempting to load a knowledge from quiz {filepath}", e)
        for question_type in quiz_dat:
            if question_type not in [
                "GapFillingQuestion",
                "SentenceMakingQuestion",
                "ListeningQuestion"
            ]:
                logger.error(f"Quiz.load() : unknown question class : {question_type}")
                continue
            question_class = eval(question_type)
            for q_dat in quiz_dat[question_type]:
                content = q_dat["content"]
                solution = q_dat["solution"]
                analysis = q_dat.get("analysis", None)
                rela_nodes = []
                for m_id in q_dat["rela_nodes"]:
                    try:
                        rela_node = retriever.match_node(
                            {"m_id": m_id}
                        )[0]
                        rela_nodes.append(rela_node)
                    except Exception as e:
                        logger.error(f"Quiz.load() : an error occurred while attempting to load a question from quiz : {filepath}", e)
                q = question_class(content, solution, rela_nodes, analysis)
                quiz.addq(q)
            quiz.filepath = filepath
        return quiz