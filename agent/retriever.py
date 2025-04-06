import os, asyncio
import yaml
from pathlib import Path
from shortuuid import uuid
from typing import (
    Dict, List, Tuple, Literal, Any
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
                raise RuntimeError(f"MemoryNode.__init__() : {key} not found in the node : {node}")
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
            logger.error(f"MemoryNode.destroy() : an error occurred while attempting to delete the node in the vector DB: {self._node}", e)
            return False
        try:
            self._node._destroy()
            logger.info(f"MemoryNode.destroy() : a node was successfully deleted in memory : {self._node}")
            return True
        except Exception as e:
            logger.error(f"MemoryNode.destory() : an error occurred while attempting to delete the node in the graph DB: {self._node}", e)
            self._collection.add([m_id], documents=[abstract])
            logger.info(f"MemoryNode.destroy() : rollback... successully added the node back to vector DB: {self._node}")
            return False
    
    def dic(self) -> Dict[str, Any]:
        return self._node._properties
    
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
        uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
        username = "neo4j"
        password = os.environ.get("NEO4J_PASSWORD", "clara-neo4j")
        
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
                logger.error(f"MemoryManager.add_node() : `{key}` not found in node profile")
                return None
        m_id = uuid()
        node_profile["m_id"] = m_id
        abstract = node_profile["abstract"]
        label = node_profile.pop("label")
        try:
            self.__collection.add([m_id], documents=[abstract])
        except Exception as e:
            logger.error(f"MemoryManager.add_node() : an error occurred while attempting to add the node in the vector DB : [{label}]\n{node_profile}", e)
            return None
        try:
            node = self.__graph.create_node(label, node_profile)
            logger.info(f"MemoryManager.add_node() : successfully added the node : {node}")
            memory_node = MemoryNode(node, self.__collection)
            return memory_node
        except Exception as e:
            # Rollback
            logger.error(f"MemoryManager.add_node() : an error occurred while attempting to add the node in the graph DB : [{label}]\n{node_profile}", e)
            self.__collection.delete([m_id])
            logger.info(f"MemoryManager.add_node() : rollback... successfully deleted node(mid = {m_id}) in vector DB.")
            return None
    
    def match_node(self,
                   node_profile: Dict[str, str | int | float] = {},
                   order: Tuple[str, Literal["ASC", "DESC"]] | None = None,
                   skip: int | None = None,
                   limit: int | None = None
                   ) -> List[MemoryNode]:
        m_id = node_profile.pop("m_id", None)
        label = node_profile.pop("label", None)
        
        node_list = self.__graph.match_node(m_id, label, node_profile, order, skip, limit)
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
            logger.error(f"MemoryManager.query() : an error occurred while attempting to query similar nodes with query abstract: '{query_abstract}', n_rela = {n_rela}", e)
            return []
    
    def close(self):
        self.__graph.close()

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
            sys_prompt = self.all_prompts["create_rela_others"]["sys_prompt"]
            few_shots = self.all_prompts["create_rela_others"]["few_shots"]
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
            if "label" not in response:
                response["label"] = "relative"
            return response
        except Exception as e:
            logger.error(f"Retriever.__gen_rela() : an error occurred while attempting to generate the relationship between 2 nodes:\n{n1}\n{n2}", e)
            return None
    
    def match_node(self,
                   node_profile: Dict[str, str | int | float] = {},
                   order: Tuple[str, Literal["ASC", "DESC"]] | None = None,
                   skip: int | None = None,
                   limit: int | None = None
                   ) -> List[MemoryNode]:
        return self.memory.match_node(node_profile, order, skip, limit)
    
    def match(self,
              from_prop: Dict[str, str | int | float],
              to_prop: Dict[str, str | int | float],
              rela_prop: Dict[str, str | int | float],
              bidirect: bool = False
              ) -> List[Tuple[MemoryNode, Relationship, MemoryNode]]:
        return self.memory.match(from_prop, to_prop, rela_prop, bidirect)
        
    def remember(self, node_profile: Dict[str, str | int | float], n_rela: int = 5) -> MemoryNode:
        async def gen_rela(fr: MemoryNode, to: MemoryNode):
            rela = await self.__gen_rela(fr, to)
            if rela is not None and "label" in rela:
                label = rela.pop("label")
                fr.create_rela(to, label, rela)
        try:
            sim_nodes = self.memory.query(node_profile["abstract"], n_rela) if n_rela > 0 else []
            if len(sim_nodes) > 0 and sim_nodes[0].label == node_profile["label"] and sim_nodes[0].get_prop("abstract") == node_profile["abstract"]:
                # TODO merge the memory
                return sim_nodes[0]
            node = self.memory.add_node(node_profile)
            coro_list = []
            for sim_node in sim_nodes:
                coro_list.append(gen_rela(node, sim_node))
            if len(coro_list) > 0:
                asyncio.run(asyncio.wait(coro_list, timeout=None))
            return node
        except Exception as e:
            logger.error(f"Retriever.remember() : an error occurred while attempting to remember the the node: {node_profile}", e)
            return None
    
    def close(self):
        self.memory.close()
        self.engine.close()
    
    @requires_superuser
    def clear_all(self):
        nodes = self.memory.match_node()
        for node in nodes:
            if node.destroy():
                logger.info(f"Retriever.clear_all() : successfully deleted the node : {node}")