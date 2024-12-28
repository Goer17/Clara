import os, asyncio
import yaml
from pathlib import Path
from shortuuid import uuid
from typing import (
    Dict, List, Tuple, Literal
)
from chromadb import PersistentClient, Collection
from utils.neo4j_orm import (
    Graph, Node, Relationship
)
from utils.general import (
    LLMEngine
)
from utils.logger import logger
from utils.string import Formatter

class MemoryNode:
    def __init__(self,
                 node: Node,
                 collection: Collection
                 ):
        for key in ["abstract", "content"]:
            if key not in node._properties:
                raise RuntimeError(f"MemoryNode.__init__() : {key} not found in node : {node}")
        self._node: Node = node
        self._collection: Collection = collection
    
    @property
    def label(self):
        return self._node.label
    
    def __str__(self):
        return self._node.__str__()

    def get_prop(self, key: str) -> str | int | float:
        return self._node.get_prop(key)
    
    def set_prop(self, key: str, value: str | int | float):
        self._node.set_prop(key, value)
    
    def remove_prop(self, key: str):
        self._node.remove_prop(key)
    
    def set_label(self, label: str):
        self._node.set_label(label)
    
    def update(self):
        self._node.update()
    
    def create_rela(self, to: 'MemoryNode', label: str, properties: Dict[str, str | int | float]) -> Relationship:
        return self._node.create_rela(to._node, label, properties)
    
    def destroy(self) -> bool:
        m_id = self._node.m_id
        abstract = self._node._properties["abstract"]
        try:
            self._collection.delete([m_id])
        except Exception as e:
            logger.error(f"MemoryNode::destroy : One error occcurred when deleting the node in vectorDB, node(mid = {self._node.m_id})")
            return False
        try:
            self._node._destroy()
            return True
        except Exception as e:
            logger.error(f"MemoryNode::destory : One error occurred when deleting the node in graph DB: {self._node}")
            logger.info(f"Rollback...")
            self._collection.add([m_id], documents=[abstract])
            return False
    
    def text(self, enclose: bool = False) -> str:
        result = (
            f"label: {self._node.label}\n",
            f"abstract: {self._node.get_prop('abstract')}\n"
            f"content:\n{self._node.get_prop('content')}\n"
        )
        if enclose:
            result = f"```txt\n{result}\n```"
        
        return result


class MemoryManager:
    def __init__(self):
        uri = "bolt://localhost:7687"
        username = "neo4j"
        password = "Yy030518neo4j"
        
        self.__graph = Graph(
            uri=uri,
            auth=(username, password)
        )
        
        chroma_client = PersistentClient()
        self.__collection = chroma_client.get_or_create_collection("vector_db")
    
    def add_node(self, node_profile: Dict[str, str | int | float]) -> MemoryNode:
        for key in [
            "label",
            "abstract",
            "content"
        ]:
            if key not in node_profile:
                logger.error(f"MemoryManager::add_node : `{key}` not found in node profile")
                return None
        m_id = uuid()
        node_profile["m_id"] = m_id
        abstract = node_profile["abstract"]
        label = node_profile.pop("label")
        try:
            self.__collection.add([m_id], documents=[abstract])
        except Exception as e:
            logger.error(f"MemoryManager::add_node : One error occurred when adding a node : [{label}]\n{node_profile} -> {e}")
            return None
        try:
            node = self.__graph.create_node(label, node_profile)
            logger.info(f"MemoryManager::add_node : successfully added node : {node}")
            memory_node = MemoryNode(node, self.__collection)
            return memory_node
        except Exception as e:
            # Rollback
            logger.error(f"MemoryManager::add_node : One error occurred when adding a node : [{label}]\n{node_profile} -> {e}")
            self.__collection.delete([m_id])
            logger.info(f"MemoryManager::add_node : rollback... deleted node(mid = {m_id}) in vector DB.")
            return None
    
    def match_node(self,
                   node_profile: Dict[str, str | int | float] = {},
                   order: Tuple[str, Literal["ASC", "DESC"]] | None = None,
                   limit: int | None = None
                   ) -> List[MemoryNode]:
        m_id = node_profile.pop("m_id", None)
        label = node_profile.pop("label", None)
        
        node_list = self.__graph.match_node(m_id, label, node_profile, order, limit)
        memory_node_list = [MemoryNode(node, self.__collection) for node in node_list]
        
        return memory_node_list
    
    def match(self,
              from_prop: Dict[str, str | int | float],
              to_prop: Dict[str, str | int | float],
              rela_prop: Dict[str, str | int | float],
              bidirect: bool = False
              ) -> List[Tuple[MemoryNode, Relationship, MemoryNode]]:

        results = self.__graph.match(from_prop, to_prop, rela_prop, bidirect)
        memory_results = [
            (MemoryNode(p, self.__collection), r, MemoryNode(q, self.__collection)) for p, r, q in results
        ]
        return memory_results

    def query(self,
              query_abstract: str,
              n_rela: int
              ) -> List[MemoryNode]:
        try:
            m_ids = self.__collection.query(query_texts=[query_abstract], n_results=n_rela)["ids"][0]
            memory_node_list = []
            for m_id in m_ids:
                memory_node = self.match_node({"m_id": m_id})[0]
                memory_node_list.append(memory_node)
            return memory_node_list
        except Exception as e:
            logger.error(f"MemoryManager::query : One error occurred when query similar nodes with abstract: '{query_abstract}', n_rela = {n_rela} : {e}")
            return []

class Retriever:
    def __init__(self, engine: LLMEngine):
        self.engine = engine
        self.memory = MemoryManager()
        retriever_path = Path("config") / "prompts" / "retriever.yml"
        with open(retriever_path) as f:
            self.all_prompts = yaml.safe_load(f)
    
    @staticmethod
    def requires_superuser(method):
        def wrapper(self, *args, **kwargs):
            if os.geteuid() != 0:
                raise RuntimeError(f"Error: Method '{method.__name__}' requires superuser privileges.")
            return method(self, *args, **kwargs)
        return wrapper
    
    def __gen_rela_prompts(self, n1: MemoryNode, n2: MemoryNode):
        if n1.label in ["word", "unfamiliar_word"] and n2.label in ["word", "unfamiliar_word"]:
            sys_prompt = self.all_prompts["create_rela_word2word"]["sys_prompt"]
            few_shots = self.all_prompts["create_rela_word2word"]["few_shots"]
        else:
            pass
        prompt = f"{n1.text(enclose=True)}\n{n2.text(enclose=True)}"
        
        return sys_prompt, few_shots, prompt
    
    async def __gen_rela(self, n1: MemoryNode, n2: MemoryNode) -> Dict[str, str | int | float]:
        sys_prompt, few_shots, prompt = self.__gen_rela_prompts(n1, n2)
        response = await self.engine.async_generate(
            prompt=prompt,
            sys_prompt=sys_prompt,
            few_shots=few_shots
        )
        if "NO_RELA" in response:
            return None
        try:
            response = Formatter.catch_json(response)
            return response
        except Exception as e:
            logger.error(f"Retriever::__gen_rela() : One error occurred : {e}")
            return None
    
    def remember(self, node_profile: Dict[str, str | int | float], n_rela: int = 5) -> bool:
        async def gen_rela(fr: MemoryNode, to: MemoryNode):
            rela = await self.__gen_rela(fr, to)
            if rela is not None and "label" in rela:
                label = rela.pop("label")
                fr.create_rela(to, label, rela)
        try:
            sim_nodes = self.memory.query(node_profile["abstract"], n_rela)
            if len(sim_nodes) > 0 and sim_nodes[0].get_prop("abstract") == node_profile["abstarct"]:
                # TODO merge the memory
                return True
            node = self.memory.add_node(node_profile)
            coro_list = []
            for sim_node in sim_nodes:
                coro_list.append(gen_rela(node, sim_node))
            asyncio.run(asyncio.wait(coro_list, timeout=None))
            return True
        except Exception as e:
            logger.error(f"Retriever::remember() : {e}")
            return False
    
    @requires_superuser
    def clear_all(self):
        nodes = self.memory.match_node()
        for node in nodes:
            if node.destroy():
                logger.info(f"Retriever::clear_all() : deleted node : {node}")
            else:
                logger.error(f"Retriever::clear_all() : one error occurred when deleting node : {node}")