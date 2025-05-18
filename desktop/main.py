# desktop/main.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

# Define diretório de dados para salvar os JSON
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# === Model ===
class PlayerStats:
    def __init__(self):
        self.goals = 0
        self.yellow = 0
        self.red = 0

    def increment(self, stat: str, delta: int = 1):
        current = getattr(self, stat)
        new_value = max(0, current + delta)
        setattr(self, stat, new_value)

# === Persistence Manager ===
class MatchManager:
    def __init__(self, match_name: str, team_a: str, team_b: str, num_players: int = None):
        safe_name = match_name.replace(' ', '_')
        self.data_dir = DATA_DIR
        self.file_name = os.path.join(self.data_dir, f"match-{safe_name}.json")
        self.current_file = os.path.join(self.data_dir, "current-match.json")
        self.match_name = match_name
        self.team_a = team_a
        self.team_b = team_b
        self.num_players = num_players
        self.data = None

    def load_or_create(self, players_a: list, players_b: list):
        if not os.path.exists(self.file_name):
            teams = [
                {"team": self.team_a, "players": [{"name": name, "goals": 0, "yellow": 0, "red": 0} for name in players_a]},
                {"team": self.team_b, "players": [{"name": name, "goals": 0, "yellow": 0, "red": 0} for name in players_b]}
            ]
            self.data = {"match_name": self.match_name, "teams": teams}
            self._save_file(self.file_name)
        else:
            with open(self.file_name, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if 'teams' not in loaded and 'players' in loaded:
                # Converte formato legado para o novo esquema
                self.data = {"match_name": self.match_name, "teams": []}
                # Time A
                self.data['teams'].append({
                    "team": self.team_a,
                    "players": []
                })
                # Time B
                self.data['teams'].append({
                    "team": self.team_b,
                    "players": []
                })
                for i, name in enumerate(players_a):
                    stats_a = loaded['players'][i]['team_a']
                    self.data['teams'][0]['players'].append({"name": name, **stats_a})
                for i, name in enumerate(players_b):
                    stats_b = loaded['players'][i]['team_b']
                    self.data['teams'][1]['players'].append({"name": name, **stats_b})
                self._save_file(self.file_name)
            else:
                self.data = loaded
        self._save_file(self.current_file)
        return self.data

    def update_stat(self, player_index: int, team_flag: str, stat: str, value: int):
        team_name = self.team_a if team_flag == 'A' else self.team_b
        for t in self.data['teams']:
            if t['team'] == team_name:
                t['players'][player_index - 1][stat] = value
                break
        self._save_file(self.file_name)
        self._save_file(self.current_file)

    def update_teams(self, new_a: str, new_b: str, players_a: list, players_b: list):
        self.team_a = new_a
        self.team_b = new_b
        self.data['teams'][0]['team'] = new_a
        self.data['teams'][1]['team'] = new_b
        # Atualiza nomes de jogadores mantendo estatísticas
        for i, name in enumerate(players_a):
            self.data['teams'][0]['players'][i]['name'] = name
        for i, name in enumerate(players_b):
            self.data['teams'][1]['players'][i]['name'] = name
        self._save_file(self.file_name)
        self._save_file(self.current_file)

    def _save_file(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

# === View/Controller ===
class StatsWidget(tk.Frame):
    def __init__(self, parent, stats: PlayerStats, manager: MatchManager, team: str, index: int, label: str, key: str):
        super().__init__(parent)
        self.stats = stats
        self.manager = manager
        self.team = team
        self.index = index
        self.key = key
        for col in range(4): self.grid_columnconfigure(col, weight=1)
        tk.Label(self, text=f"{label}:").grid(row=0, column=0, sticky='e')
        tk.Button(self, text="-", width=2, command=lambda: self.change(-1)).grid(row=0, column=1, sticky='e', padx=2)
        self.var = tk.IntVar(value=getattr(self.stats, key))
        tk.Label(self, textvariable=self.var, width=3).grid(row=0, column=2, sticky='e', padx=2)
        tk.Button(self, text="+", width=2, command=lambda: self.change(1)).grid(row=0, column=3, sticky='e', padx=2)
    def change(self, delta: int):
        self.stats.increment(self.key, delta)
        self.manager.update_stat(self.index, self.team, self.key, getattr(self.stats, self.key))
        self.var.set(getattr(self.stats, self.key))

class PlayerRow(tk.Frame):
    def __init__(self, parent, index: int, manager: MatchManager, name_a: str, name_b: str, stats_a: dict, stats_b: dict):
        super().__init__(parent)
        self.index = index
        self.manager = manager
        self.stats_a = PlayerStats(); self.stats_b = PlayerStats()
        for k in ('goals','yellow','red'):
            setattr(self.stats_a, k, stats_a[k]); setattr(self, 'stats_b', self.stats_b)
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=0); self.grid_columnconfigure(2, weight=1)
        tk.Label(self, text=name_a).grid(row=0, column=0)
        sep = ttk.Separator(self, orient='vertical'); sep.grid(row=0, column=1, rowspan=4, sticky='ns', padx=10)
        tk.Label(self, text=name_b).grid(row=0, column=2)
        stats_info = [("Gols",'goals'), ("Cartões Amarelos",'yellow'), ("Cartões Vermelhos",'red')]
        for i,(lbl,key) in enumerate(stats_info,1):
            StatsWidget(self,self.stats_a,manager,'A',index,lbl,key).grid(row=i,column=0,sticky='e',padx=5,pady=2)
            StatsWidget(self,self.stats_b,manager,'B',index,lbl,key).grid(row=i,column=2,sticky='e',padx=5,pady=2)

class MatchApp:
    def __init__(self):
        base = DATA_DIR
        with open(os.path.join(base, 'teams.json'), 'r', encoding='utf-8') as f:
            self.teams = json.load(f)
        self.root = tk.Tk(); self.root.title("Placar da Partida")
        self.player_rows = []
        self.manager = None
        self._build_ui()
        self.root.mainloop()
    def _build_ui(self):
        selects = tk.Frame(self.root); selects.pack(fill='x', pady=(10,5))
        names = [t['name'] for t in self.teams]
        tk.Label(selects, text="Time A:").grid(row=0, column=0, padx=5)
        self.cmb_a = ttk.Combobox(selects, values=names, state='readonly'); self.cmb_a.current(0); self.cmb_a.grid(row=0, column=1)
        tk.Label(selects, text="Time B:").grid(row=0, column=2, padx=20)
        self.cmb_b = ttk.Combobox(selects, values=names, state='readonly'); self.cmb_b.current(1 if len(names)>1 else 0); self.cmb_b.grid(row=0, column=3)
        self.cmb_a.bind('<<ComboboxSelected>>', self.on_team_change)
        self.cmb_b.bind('<<ComboboxSelected>>', self.on_team_change)
        info = tk.Frame(self.root); info.pack(fill='x', pady=(0,10))
        tk.Label(info, text="Nome da Partida:").grid(row=0, column=0, padx=5)
        self.match_var = tk.StringVar(); tk.Entry(info, textvariable=self.match_var, width=25).grid(row=0, column=1)
        tk.Button(info, text="Save", command=self.on_save).grid(row=0, column=2, padx=10)
    def on_save(self):
        name = self.match_var.get().strip()
        if not name: messagebox.showwarning("Aviso","Digite o nome da partida."); return
        a, b = self.cmb_a.get(), self.cmb_b.get()
        data_a = next(t for t in self.teams if t['name']==a)
        data_b = next(t for t in self.teams if t['name']==b)
        players_a = [p['name'] for p in data_a['players']]
        players_b = [p['name'] for p in data_b['players']]
        self.manager = MatchManager(name, a, b, num_players=len(players_a))
        match_data = self.manager.load_or_create(players_a, players_b)
        self._render_rows(match_data)
    def on_team_change(self, event):
        if not self.manager: return
        new_a, new_b = self.cmb_a.get(), self.cmb_b.get()
        data_a = next(t for t in self.teams if t['name']==new_a)
        data_b = next(t for t in self.teams if t['name']==new_b)
        players_a = [p['name'] for p in data_a['players']]
        players_b = [p['name'] for p in data_b['players']]
        self.manager.update_teams(new_a, new_b, players_a, players_b)
        self._render_rows(self.manager.data)
    def _render_rows(self, match_data: dict):
        for row in self.player_rows: row.destroy()
        self.player_rows.clear()
        for i, p_info in enumerate(match_data['teams'][0]['players'], start=1):
            pa_name = p_info['name']; pb_info = match_data['teams'][1]['players'][i-1]
            row = PlayerRow(self.root, i, self.manager, pa_name, pb_info['name'], p_info, pb_info)
            row.pack(fill='x', pady=5, padx=10); self.player_rows.append(row)

if __name__ == "__main__": MatchApp()
