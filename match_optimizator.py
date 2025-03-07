import json
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from create_tables import DataManager


class MatchOptimizator(DataManager):
    current_layer : int
    branch_graph : nx.Graph
    pruning_factor : float


    def __init__(self, pruning_factor : float = 1):
        super().__init__()
        self.branch_graph = nx.Graph()
        self.current_layer = 0
        self.node_id = 1
        self.pruning_factor = pruning_factor

    def optimizator(self, pruning_factor : float = 1):
        self.branch_graph.add_node(0, layer = -1)
        for i in range(10):
            print(f"{i} iteración")
            self.current_layer = i
            self.generate_branches(pruning_factor)
        self.calculate_solution(i)

    def generate_branches(self, pruning_factor : float):
        df_matches = self.df_matches
        current_layer = self.current_layer
        branch_graph = self.branch_graph
        previous_layer_list = [node for node, layer in nx.get_node_attributes(branch_graph, 'layer').items() if layer == current_layer - 1]
        previous_layer_list = self.poda(previous_layer_list, pruning_factor)
        match = df_matches.loc[current_layer, "Partido"]
        schedule_list = [(date, hour, value) for hour, row in self.df_schedule.iterrows() for date, value in row.items()]
        for schedule in schedule_list:
            date = schedule[0]
            hour = schedule[1]
            value = schedule[2]
            if not value or pd.isnull(value):
                continue
            else:
                for previous_node in previous_layer_list:
                    
                    branch_graph.add_node(self.node_id, hour=hour,
                                            date=date, layer = self.current_layer, match = match, date_pon = value)
                    branch_graph.add_edge(previous_node, self.node_id)
                    self.calculate_ponderacion_total(self.node_id, match)
                    self.node_id += 1
        self.branch_graph = branch_graph
        
            
    def calculate_ponderacion_total(self, nodeId : int, match: str):
        total_pon = 0
        previous_nodes = nx.shortest_path(self.branch_graph, source=0, target=nodeId)
        self.calculate_match_coincidence(previous_nodes)
        self.calculate_teams_ponderacion(nodeId, match)
        for previous_nodeId in previous_nodes : 
            nodo_data = self.branch_graph.nodes(data=True)[previous_nodeId]
            coinci_pon = nodo_data.get("coinci_pon")
            cat_pon = nodo_data.get("cat_pon")
            date_pon = nodo_data.get("date_pon")
            if not cat_pon or not coinci_pon or not date_pon:
                continue
            total_pon += coinci_pon * cat_pon * date_pon
        self.branch_graph.nodes[nodeId]["total_pon"] = total_pon

      

    def calculate_teams_ponderacion(self, nodeId : int, match : str) :
        equipo1 , equipo2 = match.split(" - ")
        mask1 = self.df_team_cat["Equipos"] == equipo1
        mask2 = self.df_team_cat["Equipos"] == equipo2
        cat1 = "Categoria " + self.df_team_cat.loc[mask1, "Categorias"].values[0]
        cat2 = "Categoria " + self.df_team_cat.loc[mask2, "Categorias"].values[0]
        ponderacion = float(self.df_cat_fact.at[cat1, cat2])
        if not ponderacion:
            raise Exception("Ha habido un problema obteniendo la ponderacion de algun partido")
        self.branch_graph.nodes[nodeId]['cat_pon'] = ponderacion

    def calculate_solution(self, current_layer : int):
        last_layer_list = [node for node, layer in nx.get_node_attributes(self.branch_graph, 'layer').items() if layer == current_layer]
        

        todos_valores = { n : self.branch_graph.nodes[n]['total_pon'] for n in last_layer_list}
        id_max = max(todos_valores, key= todos_valores.get)
        valor_max = todos_valores[id_max]
        self.draw_branch(0, id_max)
        previous_nodes = nx.shortest_path(self.branch_graph, source=0, target=id_max)
        df = pd.DataFrame([
            {
                'nodoId': nodo,
                'match': self.branch_graph.nodes[nodo]['match'],  # Atributo 'match'
                'hour': self.branch_graph.nodes[nodo]['hour'],    # Atributo 'hour'
                'date': self.branch_graph.nodes[nodo]['date']     # Atributo 'date'
            }
            for nodo in previous_nodes if nodo != 0
        ])
        print(df)
        print(" Esta es la cantidad de espectadores totales calculada para la anterior solución: "+ str(valor_max) + " millones de viewers")

    def count_frecuency(self, string_list : list):
        frecuency = {}
        for elemento in string_list:
            if elemento in frecuency:
                frecuency[elemento] += 1
            else:
                frecuency[elemento] = 0
        return frecuency

    def calculate_match_coincidence(self, previous_nodes: list[int]):
        node_coincidence_dict = {}   
        date_list = [self.branch_graph.nodes[n]["date"] + self.branch_graph.nodes[n]["hour"] for n in previous_nodes if "date" in self.branch_graph.nodes[n]] 
        coinci_dict = self.count_frecuency(date_list) 
        for node in previous_nodes:
            node_data = self.branch_graph.nodes[node]
            if node_data.get("date") and node_data.get("date") + node_data.get("hour") in coinci_dict.keys():
                filt = self.df_coincidence_fact["Numero_coincidencia"] = coinci_dict.get(node_data.get("date") + node_data.get("hour"))
                audience_rating = float(self.df_coincidence_fact.loc[filt, "Factor_audiencia"])
                node_coincidence_dict[node] = audience_rating

        nx.set_node_attributes(self.branch_graph, {node_id: {'coinci_pon': audience_rating} for node_id, audience_rating in node_coincidence_dict.items()})
        
    def poda(self, last_layer_list : list, pruning_factor : int) -> list:
        nodos_a_eliminar = []
        if len(last_layer_list) > 5:
            todos_valores = [self.branch_graph.nodes[n]['total_pon'] for n in last_layer_list]
            valor_medio = sum(todos_valores) / len(last_layer_list)
            valor_max = max(todos_valores)
            print("Esta es la cantidad de nodos: " + str(len(last_layer_list)) + " .Y este es su valor medio: " + str(valor_medio) + " Y este su valor maximo: "+ str(valor_max))
            extra = len(last_layer_list)/100000 * pruning_factor
            nodos_a_eliminar = [n for n in last_layer_list if self.branch_graph.nodes[n]['total_pon'] < valor_medio + extra]
            
            # Los eliminamos
            self.branch_graph.remove_nodes_from(nodos_a_eliminar)
        response = [nodoId for nodoId in last_layer_list if nodoId not in nodos_a_eliminar]
        return response
        

    def draw_graph(self):
        # Dibujar el grafo
        # Usar una disposición jerárquica para el grafo

        plt.figure(figsize=(12, 8)) 
        # pos = nx.spring_layout(self.branch_graph)  # Genera una disposición para los nodos
        pos = nx.multipartite_layout(self.branch_graph, subset_key="layer")
        pos = {node: (y, -x) for node, (x, y) in pos.items()}  # Intercambia x e y
        # Dibuja los edges con mayor transparencia y líneas más delgadas
        nx.draw(
            self.branch_graph,
            pos,
            with_labels=False,  # Desactiva las etiquetas iniciales de los nodos
            node_color='skyblue',
            node_size=200,
            font_size=10,
            edge_color='gray',  # Color de los edges
            width=0.5,          # Grosor más delgado para los edges
            alpha=0.2           # Aumenta la transparencia de los edges
        )

       
        node_labels = {
            node: f"{node}\n" + "\n".join(f"{key}: {value}" for key, value in data.items())
            for node, data in self.branch_graph.nodes(data=True) 
        }
        label_offset = 0
        label_positions = {node: (x - label_offset, y - label_offset) for node, (x, y) in pos.items()}
        # Dibujar las etiquetas de los nodos
        nx.draw_networkx_labels(self.branch_graph, pos, labels=node_labels, font_size=5, font_color='brown')

        # Mostrar el grafo
        plt.title("Visualización del Grafo")
        plt.show()


    def draw_branch(self, start_node, end_node):
        """
        Dibuja una rama específica del árbol desde el nodo start_node hasta end_node.
        """
        # Obtener la lista de nodos en la rama
        path_nodes = nx.shortest_path(self.branch_graph, source=start_node, target=end_node)
        
        # Crear un subgrafo con los nodos de la rama
        branch_subgraph = self.branch_graph.subgraph(path_nodes)

        # Generar la disposición para los nodos de la rama usando la capa
        pos = nx.multipartite_layout(self.branch_graph, subset_key="layer")
        pos = {node: (y, -x) for node, (x, y) in pos.items() if node in path_nodes}  # Filtrar solo los nodos de la rama

        # Dibujar los edges con mayor transparencia y líneas más delgadas
        plt.figure(figsize=(8, 6))
        nx.draw(
            branch_subgraph,
            pos,
            with_labels=True,
            node_color='lightcoral',
            node_size=300,
            font_size=8,
            edge_color='black',
            width=1,
            alpha=0.6
        )

        # Etiquetas de los nodos con todos los atributos disponibles
        node_labels = {
            node: f"{node}\n" + "\n".join(f"{key}: {value}" for key, value in data.items())
            for node, data in self.branch_graph.nodes(data=True) if node in path_nodes
        }

        # Posiciones de etiquetas con un pequeño desplazamiento
        label_offset = 0.02
        label_positions = {node: (x - label_offset, y - label_offset) for node, (x, y) in pos.items()}

        # Dibujar etiquetas de nodos
        nx.draw_networkx_labels(branch_subgraph, pos, labels=node_labels, font_size=6, font_color='brown')

        plt.title("Visualización de la Rama")
        plt.show()



if __name__ == "__main__":
    matchOptimizator = MatchOptimizator()
    matchOptimizator.optimizator(pruning_factor=1)
    