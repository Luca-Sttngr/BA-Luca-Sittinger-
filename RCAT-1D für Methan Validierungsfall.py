import os
import math
import numpy as np
import CoolProp.CoolProp as CP
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

###------------------------------------------------------------------------------------------###
### ------------------ 0. DATEN EINLESEN (Twg, Twi, Twc aus eigener X-Y-Datei) -------------- ###
###------------------------------------------------------------------------------------------###

dateipfad = r""
daten = []
twg_daten = []

if os.path.exists(dateipfad):
    with open(dateipfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    x_mm = float(parts[0].replace(',', '.').strip())
                    twg_val = float(parts[1].replace(',', '.').strip())
                    
                    # Liest Twi (Spalte 3) und Twc (Spalte 4) ein, falls sie existieren, ansonsten 0.0
                    twi_val = float(parts[2].replace(',', '.').strip()) if len(parts) >= 3 else 0.0
                    twc_val = float(parts[3].replace(',', '.').strip()) if len(parts) >= 4 else 0.0
                    
                    daten.append({
                        'Location': x_mm,
                        'Temp_Twg': twg_val,
                        'Temp_Twi': twi_val,
                        'Temp_Twc': twc_val
                    })
                    
                    twg_daten.append((x_mm / 1000.0, twg_val))
                except ValueError:
                    pass

twg_x_m = [p[0] for p in twg_daten]
twg_val_k = [p[1] for p in twg_daten]

### ------------------ 0b. KONTUR EINLESEN (Minimaler Parser ohne Output) ------------------- ###
###------------------------------------------------------------------------------------------###

kontur_pfad = r""
kontur_daten = []

if os.path.exists(kontur_pfad):
    with open(kontur_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    kontur_daten.append((float(parts[0]) / 1000.0, float(parts[1]) / 1000.0))  # mm -> m
                except ValueError:
                    pass

kontur_x_m = [p[0] for p in kontur_daten]
kontur_r_m = [p[1] for p in kontur_daten]


###------------------------------------------------------------------------------------------###
### ------------------ 0c. KANALGEOMETRIE EINLESEN (Breite b und Höhe h) ------------------- ###
###------------------------------------------------------------------------------------------###

kanal_b_pfad = r""
kanal_h_pfad = r""

kanal_b_daten = []
if os.path.exists(kanal_b_pfad):
    with open(kanal_b_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    x_val = float(parts[0].replace(',', '.').strip()) / 1000.0  # mm -> m
                    b_val = float(parts[1].replace(',', '.').strip()) / 1000.0  # mm -> m
                    kanal_b_daten.append((x_val, b_val))
                except ValueError:
                    pass

kanal_xb_m = [p[0] for p in kanal_b_daten]
kanal_b_m = [p[1] for p in kanal_b_daten]

kanal_h_daten = []
if os.path.exists(kanal_h_pfad):
    with open(kanal_h_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    x_val = float(parts[0].replace(',', '.').strip()) / 1000.0  # mm -> m
                    h_val = float(parts[1].replace(',', '.').strip()) / 1000.0  # mm -> m
                    kanal_h_daten.append((x_val, h_val))
                except ValueError:
                    pass

kanal_xh_m = [p[0] for p in kanal_h_daten]
kanal_h_m = [p[1] for p in kanal_h_daten]


kanal_s_pfad = r""

kanal_s_daten = []
if os.path.exists(kanal_s_pfad):
    with open(kanal_s_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    x_val = float(parts[0].replace(',', '.').strip()) / 1000.0  # mm -> m
                    s_val = float(parts[1].replace(',', '.').strip()) / 1000.0  # mm -> m
                    kanal_s_daten.append((x_val, s_val))
                except ValueError:
                    pass

kanal_xs_m = [p[0] for p in kanal_s_daten]
kanal_s_m = [p[1] for p in kanal_s_daten]


###------------------------------------------------------------------------------------------###
### ------------------ 0d. HEAT FLUX EINLESEN (MW/m^2 aus eigener Datei) ------------------- ###
###------------------------------------------------------------------------------------------###

q_pfad = r""
q_daten_neu = []

if os.path.exists(q_pfad):
    with open(q_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            # Akzeptiert wieder ';' oder Leerzeichen als Trenner
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    # x-Wert einlesen (Annahme: mm, daher / 1000 für m)
                    x_val = float(parts[0].replace(',', '.').strip()) / 1000.0  
                    
                    # q-Wert einlesen (in MW/m^2) und direkt in kW/m^2 umwandeln für Abschnitt 4
                    q_val_MW = float(parts[1].replace(',', '.').strip())        
                    q_val_kW = q_val_MW * 1000.0                                
                    
                    q_daten_neu.append((x_val, q_val_kW))
                except ValueError:
                    pass

# Überschreibt die q-Listen aus Abschnitt 0, falls die neue Datei existiert und eingelesen wurde.
# So merkt Abschnitt 4 überhaupt nicht, dass die Daten woanders herkommen!
if q_daten_neu:
    parsed_x_m = [p[0] for p in q_daten_neu]
    parsed_q_kw = [p[1] for p in q_daten_neu]

###------------------------------------------------------------------------------------------###
### ------------------ 0e. DRUCK UND FLUID-TEMPERATUR EINLESEN ----------------------------- ###
###------------------------------------------------------------------------------------------###

# PFADE ANPASSEN!
p_pfad       = r""
T_fluid_pfad = r""

# --- 1. Druck einlesen ---
p_daten = []
if os.path.exists(p_pfad):
    with open(p_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    x_val = float(parts[0].replace(',', '.').strip()) / 1000.0  
                    p_val = float(parts[1].replace(',', '.').strip())          
                    p_daten.append((x_val, p_val))
                except ValueError:
                    pass

p_x_m   = [p[0] for p in p_daten]
p_val_p = [p[1] for p in p_daten]

# --- 2. Fluid-Temperatur einlesen ---
T_fluid_daten = []
if os.path.exists(T_fluid_pfad):
    with open(T_fluid_pfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(';') if ';' in line else line.split()
            if len(parts) >= 2:
                try:
                    x_val = float(parts[0].replace(',', '.').strip()) / 1000.0  
                    T_val = float(parts[1].replace(',', '.').strip())          
                    T_fluid_daten.append((x_val, T_val))
                except ValueError:
                    pass

T_fluid_x_m = [p[0] for p in T_fluid_daten]
T_fluid_val_k = [p[1] for p in T_fluid_daten]




###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 1 Kühlmediumseigenschaften---------------------------###
###------------------------------------------------------------------------------------------###
 
fluid = "Methane"                                   # Kühlmedium
p = 155.6e5                                         # Druck des Kühlmediums bei Eintritt             [Pa]
Tco = 110.0                                         # Temperatur des Kühlmediums bei Eintritt        [K]
m_dot = 1.920                                       # gesamter Kühlmediumsmassestrom                 [kg/s]
dx = 1e-3                                           # Länge der einzelnen Kontrollvolumina           [m]
h_fluid = CP.PropsSI('H', 'T', Tco, 'P', p, fluid)  # Enthalpie des Kühlmediums                      [J/kg]
h_fluid_start = h_fluid
N_iter = 10                                         # Iterationszahl der Wandtemperatur              [-]
Twc_start = 400.0                                   # Startwert der Kühlkanalwandtemperatur          [K]
 
 
###------------------------------------------------------------------------------------------###
### --------------------------Abschnitt 2 Brennkammereigenschaften-------------------------- ###
###------------------------------------------------------------------------------------------###
 
λWand = 365.0                                       # Wärmeleitfähigkeit Brennkammermaterial         [W/m*K]
ks = 6.3e-6                                         # äquivalente Sandkornrauheit                    [m]
s = 0.9e-3
# Universelle Konturgrenzen
x_injektor = 0.0                                    # Konturbeginn an der Injektorplatte             [m]
x_duesenende = max(kontur_x_m)                      # Konturende der Düse                            [m]
# Konfiguration der Durchströmungsrichtung und Rauigkeit
Laufrichtung = "Gegenstrom"                         # Auswahl: "Gegenstrom" oder "Doppelstrom"
Rauheit = "Rau"                                     # Auswahl: "Glatt" oder "Rau"
 
# Brennkammerinnenkontur (aus Datenpunkten) #
def r(x):
    """Innenradius. Ausserhalb des Datenbereichs werden die Randwerte gehalten."""
    return float(np.interp(x, kontur_x_m, kontur_r_m))
 
def s_wand(x):
    """Wandstärke. Ausserhalb des Datenbereichs werden die Randwerte gehalten."""
    if kanal_s_m:
        return float(np.interp(x, kanal_xs_m, kanal_s_m))
    return s
###------------------------------------------------------------------------------------------###
### --------------------------Abschnitt 3 Kanalgeometrie------------------------------------ ###
###------------------------------------------------------------------------------------------###
 
if Laufrichtung == "Gegenstrom":
    n_hin    = 96
    n_rueck  = 0
 
    # Kanalbreite und -höhe aus den eingelesenen Dateien (Abschnitt 0c)
    def b_hin(x):
        return float(np.interp(x, kanal_xb_m, kanal_b_m))
 
    def h_hin(x):
        return float(np.interp(x, kanal_xh_m, kanal_h_m))
 
elif Laufrichtung == "Doppelstrom":
    n_hin    = 6
    n_rueck  = 12
 
    def b_hin(x):
        return 2.0e-3
 
    def h_hin(x):
        return 0.5e-3 + (1.0e-3 - 0.5e-3) * ((x - x_injektor) / (x_duesenende - x_injektor))
 
    def b_rueck(x):
        return 1.0e-3
 
    def h_rueck(x):
        return 2.0e-3
 
else:
    raise ValueError("Laufrichtung muss 'Gegenstrom' oder 'Doppelstrom' sein.")
 
n_gesamt = n_hin + n_rueck
 
 
# --- Durchgangsdefinition (Gl. 4.4 / 4.5) ---
# Startpunkt jeweils in der Mitte des ersten Kontrollvolumens
if Laufrichtung == "Doppelstrom":
    n_steps_doppelstrom = max(1, round((x_duesenende - x_injektor) / dx))    
    dx_eff_doppelstrom = (x_duesenende - x_injektor) / n_steps_doppelstrom    
 
    durchgaenge = [
        ("Hinweg",  x_injektor + dx_eff_doppelstrom / 2,    dx_eff_doppelstrom,
         x_duesenende,
         b_hin,   h_hin,   ks, n_hin),
        ("Rückweg", x_duesenende - dx_eff_doppelstrom / 2, -dx_eff_doppelstrom,
         x_injektor,
         b_rueck, h_rueck, ks, n_rueck)
    ]
 
elif Laufrichtung == "Gegenstrom":
    # Reine Gegenstromfuehrung: ein Durchgang vom Duesenende zum Injektor
    n_steps_doppelstrom = max(1, round((x_duesenende - x_injektor) / dx))     
    dx_eff_doppelstrom = (x_duesenende - x_injektor) / n_steps_doppelstrom    
 
    durchgaenge = [
        ("Gegenstrom", x_duesenende - dx_eff_doppelstrom / 2, -dx_eff_doppelstrom,
         x_injektor,
         b_hin, h_hin, ks, n_hin)
    ]

def steg_breite_doppelstrom(x):
    """Stegbreite bei gleichzeitiger Belegung des Umfangs durch beide Kanalsaetze."""
    h_mittel  = (n_hin * h_hin(x) + n_rueck * h_rueck(x)) / n_gesamt
    U_ref  = 2.0 * math.pi * (float(r(x)) + s + h_mittel / 2.0)
    belegt = n_hin * b_hin(x) + n_rueck * b_rueck(x)
    steg   = (U_ref - belegt) / n_gesamt
    if steg <= 0.0:
        print(f"WARNUNG: Stegbreite {steg*1000:.3f} mm bei x = {float(x)*1000:.2f} mm "
              f"(U = {U_ref*1000:.2f} mm, belegt = {belegt*1000:.2f} mm)")
        return 1e-3
    return steg
 
 
###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 4 Heat Flux (aus Datenpunkten)-----------------------###
###------------------------------------------------------------------------------------------###
 
q_data_x = parsed_x_m
q_data_q = parsed_q_kw
 
 
def q(x):
    """Waermestromdichte in W/m^2. Ausserhalb des Datenbereichs werden die
       Randwerte gehalten."""
    return float(np.interp(x, q_data_x, q_data_q)) * 1000.0    # kW/m^2 -> W/m^2
 




###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 5 Speicher fürs Plotten anlegen----------------------###
###------------------------------------------------------------------------------------------###
 
x_hin, Tco_hin, Twc_hin, Twg_hin, p_hin = [], [], [], [], []
rho_hin, Re_hin, Nu_hin = [], [], []
q_hin, alpha_hin, etaF_hin = [], [], []
Re_lambda_hin = []
x_rueck, Tco_rueck, Twc_rueck, Twg_rueck, p_rueck = [], [], [], [], []
rho_rueck, Re_rueck, Nu_rueck = [], [], []
q_rueck, alpha_rueck, etaF_rueck = [], [], []
Re_lambda_rueck = []
htd_roh = []
 
# Diagnose für Kap. 4.3 (Konvergenz der Wandtemperaturiteration)
iter_verlauf = []                                   # je Kontrollvolumen: Twc über die Iterationen
iter_restaenderung = []                             # je Kontrollvolumen: |Twc^(N) - Twc^(N-1)|
 
 
###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 6 und 7 Berechnungsschleife--------------------------###
###------------------------------------------------------------------------------------------###
 
# Gültigkeitsbereiche nach Kapitel 3
CHEN_KSD_MIN, CHEN_KSD_MAX = 5e-7, 5e-2                                           # Chen, Gl
CHEN_RE_MIN,  CHEN_RE_MAX  = 4e3,  4e8
STIMPSON_RAD_MIN           = 0.0028                                               # Stimpson 
NORRIS_PR_MAX, NORRIS_XI_MAX = 6.0, 2.5                                           # Norris
 
Twc_it      = Twc_start                             # Startwert, wird von KV zu KV weitergereicht    [K]
l           = 0.0                                   # Lauflänge über beide Durchgänge fortlaufend    [m]
abgebrochen = None                                  # Abbruchmeldung, None = kein Abbruch
 
for typ, x_start, dx_schritt, x_end, b_input, h_input, ks_vorgabe, n_kanal in durchgaenge:
    x = x_start
    while (dx_schritt > 0 and x <= x_end) or (dx_schritt < 0 and x >= x_end):
 
        # 6.1 Lokale Geometrie
        l            += abs(dx_schritt)                                           # Lauflänge
        b_kanal       = b_input(x) if callable(b_input) else b_input              # Kanalbreite
        h_kanal       = h_input(x) if callable(h_input) else h_input              # Kanalhöhe
        A_Kanal       = b_kanal * h_kanal                                         # Querschnittsfläche Kanal
        d_hydraulisch = (4 * A_Kanal) / (2 * (b_kanal + h_kanal))                 # hydraulischer Durchmesser 
        m_dot_kanal   = m_dot / n_kanal                                           # Massestrom pro Kanal
        s       = s_wand(x)

        # 6.2 Stoffgrößen (Kernstrom)
        try:
            rho_bulk    = CP.PropsSI('D', 'T', Tco, 'P', p, fluid)                # mittlere Dichte
            cp_bulk     = CP.PropsSI('C', 'T', Tco, 'P', p, fluid)                # spezifische Wärmekapazität
            lambda_bulk = CP.PropsSI('L', 'T', Tco, 'P', p, fluid)                # Wärmeleitfähigkeit
            eta_bulk    = CP.PropsSI('V', 'T', Tco, 'P', p, fluid)                # dynamische Viskosität
            h_bulk      = CP.PropsSI('H', 'T', Tco, 'P', p, fluid)                # spezifische Enthalpie
        except Exception:
            print(f"Abbruch durch Coolprop außerhalb der Stoffdatenbank bei x = {x*1000:.2f} mm")
            break
        nu_bulk     = eta_bulk / rho_bulk                                         # kinematische Viskosität
        c_mittel    = m_dot_kanal / (rho_bulk * A_Kanal)                          # mittlere Kanalgeschwindigkeit 
        Re          = (d_hydraulisch * c_mittel) / nu_bulk                        # Reynoldszahl, 
        Pr_bulk     = (nu_bulk * rho_bulk * cp_bulk) / lambda_bulk                # Prandtlzahl,

 
        # 6.3 Wärmestromdichte und Reibungsbeiwert
        q_lokal = q(x)
 
        if Rauheit == "Rau":
            relative_rauheit = ks / d_hydraulisch

            # Chen-Korrelation
            if not (CHEN_RE_MIN <= Re <= CHEN_RE_MAX and CHEN_KSD_MIN <= relative_rauheit <= CHEN_KSD_MAX):
                print(f"Abbruch bei Chen-Korrelation. Außerhalb des Gültigkeitsbereichs bei x = {x*1000:.2f} mm")
                break
            else:
                innen = (relative_rauheit**1.1098) / 2.8257 + 5.8506 / (Re**0.8981)
                arg   = relative_rauheit / 3.7065 - (5.0452 / Re) * math.log10(innen)
                ξ_chen = (-2 * math.log10(arg))**-2
                ξ_druckverlust = ξ_chen
        else:
            ks = 0
            ξ_glatt = (1.8 * math.log10(Re) - 1.5)**-2
            ξ_druckverlust = ξ_glatt

        # 6.4 Druckverlust
        p = p - ((abs(dx_schritt) / d_hydraulisch) * ξ_druckverlust * rho_bulk * ((c_mittel**2) / 2))
 
 
        # 6.5 bis 6.9 Iteration der Kühlkanalwandtemperatur
        verlauf = []
        for k in range(N_iter):
 
            # Stoffgrößen an der Kanalwand
            try:
                rho_wand    = CP.PropsSI('D', 'T', Twc_it, 'P', p, fluid)         # Dichte an der Wand
                cp_wand     = CP.PropsSI('C', 'T', Twc_it, 'P', p, fluid)         # nur Prüfung des Zustands
                lambda_wand = CP.PropsSI('L', 'T', Twc_it, 'P', p, fluid)         # nur Prüfung des Zustands
                eta_wand    = CP.PropsSI('V', 'T', Twc_it, 'P', p, fluid)         # nur Prüfung des Zustands
                h_wand      = CP.PropsSI('H', 'T', Twc_it, 'P', p, fluid)         # Enthalpie an der Wand
            except Exception:
                print(f"Abbruch durch Coolprop außerhalb der Stoffdatenbank bei x = {x*1000:.2f} mm")
                break

 
            cp_quer = cp_bulk if abs(Twc_it - Tco) < 1e-6 else (h_wand - h_fluid) / (Twc_it - Tco)           # Integral gemittelte Wärmekapazität
            Pr_quer = cp_quer * eta_bulk / lambda_bulk                                                       # gemittelte Prandtlzahl
 
 
            # 6.5 Nusselt-Zahl
            # Bishop Korrelation
            ξ_glatt = (1.8 * math.log10(Re) - 1.5)**-2
            Nu_Basis = (0.0069 * (Re**0.9) * (Pr_quer**0.66) * (rho_wand / rho_bulk)**0.43 * (1 + 2.4 * d_hydraulisch / l))   
 
 
            # 6.6 Rauheitskorrektur
            if Rauheit == "Rau":
                ξ_norris = ξ_chen / ξ_glatt
                if ξ_norris < 1.0:
                    print(f"Hinweis: Keine Verstärkung des Wärmeübergangs bei x = {x*1000:.2f} mm")
                    Rauheit_norris_Korrektur = 1.0
                    break
                else:
                    # Norris Gleichung begrenzen, Gl. (3.12)
                    ξ_norris_begrenzt = min(ξ_norris, NORRIS_XI_MAX)
                    Pr_norris_begrenzt = min(Pr_bulk, NORRIS_PR_MAX)
                    Rauheit_norris_Korrektur = ξ_norris_begrenzt**(0.68 * (Pr_norris_begrenzt**0.215))   
                Nu = Nu_Basis * Rauheit_norris_Korrektur
            else:
                Nu = Nu_Basis
 
 
            # 6.7 Wärmeübergangskoeffizient
            alpha_konv = (Nu * lambda_bulk) / d_hydraulisch                       
 
 
            # 6.8 Kühlrippenwirkungsgrad
            if Laufrichtung == "Doppelstrom":
                steg_breite = steg_breite_doppelstrom(x)
            else:
                Bezugsumfang_Kanalmitte = 2 * math.pi * (float(r(x)) + s + h_kanal/2)                                    # Bezugsumfang_Kanalmitte Umfang durch die Kanalmitte
                steg_breite = (Bezugsumfang_Kanalmitte - n_kanal * b_kanal) / n_kanal                                    # Länge eines Steges auf der Höhe der Kanalmitte
            
            Kühlrippenwirkunsgrad_Term = (((2*alpha_konv * steg_breite) / λWand)**0.5) * h_kanal / steg_breite              
            η_Kühlrippe = math.tanh(Kühlrippenwirkunsgrad_Term ) / Kühlrippenwirkunsgrad_Term                            # Kühlrippenwirkungsgrad
            alpha_Kühlrippenkorrektur = alpha_konv * (b_kanal + 2 * η_Kühlrippe * h_kanal) / (b_kanal + steg_breite)
 
 
            # 6.9 Neue Wandtemperatur auf Kühlkanalseite
            Twc_neu = Tco + (q_lokal / alpha_Kühlrippenkorrektur)                
            verlauf.append(Twc_neu)
            Twc_it = Twc_neu
 
        if abgebrochen:
            break
 
 
###---------------------------Abschnitt 7 Energieerhaltung und Wandtemperaturen------------------------###
 
        # 7.1 Effektive Fläche je Kanal
        A_umfang = 2 * math.pi * r(x) * abs(dx_schritt)
        if Laufrichtung == "Doppelstrom":
            A_eff = A_umfang * (b_kanal + steg_breite) / Bezugsumfang_Kanalmitte    
        else:
            A_eff = A_umfang / n_kanal
 
        # 7.2 Wandtemperatur auf Kühlkanalseite (Ergebnis der Iteration)
        Twc = Twc_it
        iter_verlauf.append(verlauf)
        iter_restaenderung.append(abs(verlauf[-1] - verlauf[-2]) if N_iter > 1 else float('nan'))
 
        # 7.3 Wandtemperatur auf Heißgasseite
        Twg = Twc + ((q_lokal * s) / λWand)

        # 7.4 Energieerhaltung
        h_fluid = h_fluid + ((q_lokal * A_eff) / m_dot_kanal)                     
 
        # 7.5 Neue Fluidtemperatur aus Coolprop abfragen
        try:
            Tco = CP.PropsSI('T', 'H', h_fluid, 'P', p, fluid)
        except Exception:
            abgebrochen = f"Abbruch: Austrittszustand außerhalb der Stoffdatenbank bei x = {x*1000:.2f} mm"
            print(abgebrochen)
            break
 
 
###---------------------------Abschnitt 8 Werte abspeichern----------------------------------###
 
        if typ in ["Gegenstrom", "Hinweg"]:
            x_hin.append(x)
            Tco_hin.append(Tco)
            Twc_hin.append(Twc)
            Twg_hin.append(Twg)
            p_hin.append(p / 1e5)
            rho_hin.append(rho_bulk)
            Re_hin.append(Re)
            Nu_hin.append(Nu)
            q_hin.append(q_lokal)
            alpha_hin.append(alpha_Kühlrippenkorrektur)
            etaF_hin.append(η_Kühlrippe)
            Re_lambda_hin.append((Re, ξ_druckverlust))
        else:                                                                     # Rückweg bei Doppelstrom
            x_rueck.append(x)
            Tco_rueck.append(Tco)
            Twc_rueck.append(Twc)
            Twg_rueck.append(Twg)
            p_rueck.append(p / 1e5)
            rho_rueck.append(rho_bulk)
            Re_rueck.append(Re)
            Nu_rueck.append(Nu)
            q_rueck.append(q_lokal)
            alpha_rueck.append(alpha_Kühlrippenkorrektur)
            etaF_rueck.append(η_Kühlrippe)
            Re_lambda_rueck.append((Re, ξ_druckverlust))
 
        x = x + dx_schritt
 
    if abgebrochen:
        break
 
 
###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 9 Verifikation der Energieerhaltung------------------###
###------------------------------------------------------------------------------------------###
 
Q_kuehlmittel = m_dot * (h_fluid - h_fluid_start)                              
 
x_fein     = np.linspace(x_injektor, x_duesenende, 5000)
q_fein     = np.array([q(x_) for x_ in x_fein])
r_fein     = np.array([r(x_) for x_ in x_fein])
Q_heissgas = np.trapz(q_fein * 2.0 * np.pi * r_fein, x_fein)                   
 
eps_rel = (Q_kuehlmittel - Q_heissgas) / Q_heissgas * 100.0                    
 
print(f"Zielschrittweite dx      : {dx*1e3:8.4f} mm")
print(f"Effektive Schrittweite   : {dx_eff_doppelstrom*1e3:8.4f} mm  ({n_steps_doppelstrom} Kontrollvolumina)")
print(f"Q_Kuehlmittel            : {Q_kuehlmittel/1000:8.3f} kW")
print(f"Q_Heissgas               : {Q_heissgas/1000:8.3f} kW")
print(f"Relative Abweichung      : {eps_rel:8.3f} %")
 
if iter_restaenderung:
    print(f"max |Twc^(N) - Twc^(N-1)|: {max(iter_restaenderung):8.4f} K   "
          f"(N = {N_iter} Durchlaeufe)")
###------------------------------------------------------------------------------------------###
### --------------------------- PUBLIKATIONS-PLOTTING (EINHEITLICH) ------------------------ ###
###------------------------------------------------------------------------------------------###

import os
import math
import numpy as np
import matplotlib.pyplot as plt

# ----------------- GLOBALES STYLING -----------------
FIG_WIDTH_IN, FIG_HEIGHT_IN = 9.5, 8.0
LW_DATA, LW_CALC, LW_AXES_SPINE = 4.5, 4.5, 1.125
LW_GRID, LW_TICKS = 1.2, 2.0
COLOR_GRID, COLOR_AXES = "#B0B0B0", "#333333"

# Einheitliche Achsen-Box fuer ALLE Plots (identische Breite und Hoehe)
PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 0.16, 0.84, 0.93, 0.13

# Anzahl der Y-Intervalle -> N_STEPS + 1 Beschriftungen (6 Ticks)
N_STEPS = 5

# ----------------- Y-ACHSEN HIER MANUELL EINSTELLEN -----------------
# Format: (Minimum, Maximum). Die Ticks werden mit linspace(min, max, 6) gesetzt.
YLIM_P1_TEMP  = (0.0, 950.0)     # Plot 1 links:  Temperatur Twg          [K]
YLIM_P1_Q     = (0.0, 90.0)       # Plot 1 rechts: Waermestromdichte q     [MW/m^2]
YLIM_P2_TEMP  = (110.0, 510.0)    # Plot 2 links:  Fluidtemperatur Tco     [K]
YLIM_P2_P     = (110.0, 160.0)    # Plot 2 rechts: Druck p                 [bar]
YLIM_P3_ERR   = (-60.0, 40.0)     # Plot 3:        Relativer Fehler        [%]
YLIM_P4_GEO   = (0.0, 5.0)        # Plot 4:        Kanalabmessungen        [mm]

# Schriftgroessen
FS_AXIS_LABEL = 36
FS_TICK_LABEL = 36
FS_LEGEND     = 28

plt.rcParams.update({
    "font.family": "serif",
    "font.size": FS_TICK_LABEL,
    "axes.titlesize": FS_AXIS_LABEL,
    "axes.labelsize": FS_AXIS_LABEL,
    "xtick.labelsize": FS_TICK_LABEL,
    "ytick.labelsize": FS_TICK_LABEL,
    "legend.fontsize": FS_LEGEND,
    "legend.handlelength": 1.5,
    "legend.markerscale": 2.5,
    "axes.linewidth": LW_AXES_SPINE,
    "grid.linewidth": LW_GRID,
    "xtick.major.width": LW_TICKS,
    "ytick.major.width": LW_TICKS,
    "lines.linewidth": LW_DATA,
    "grid.color": COLOR_GRID,
    "grid.linestyle": "--",
    "grid.alpha": 0.6,
    "axes.edgecolor": COLOR_AXES,
    "text.color": COLOR_AXES,
    "axes.labelcolor": COLOR_AXES,
    "xtick.color": COLOR_AXES,
    "ytick.color": COLOR_AXES,
})


###------------------------------------------------------------------------------------------###
### --------------------------- HILFSFUNKTIONEN -------------------------------------------- ###
###------------------------------------------------------------------------------------------###

def set_y_ticks(ax, lo, hi, n_steps=N_STEPS):
    """Setzt Grenzen und exakt n_steps+1 gleichmaessige Y-Ticks."""
    ax.set_ylim(lo, hi)
    ax.set_yticks(np.linspace(lo, hi, n_steps + 1))


def style_axis(ax, color=COLOR_AXES, side="left"):
    ax.tick_params(axis="y", colors=color, labelsize=FS_TICK_LABEL,
                   length=8, width=LW_TICKS)
    ax.spines[side].set_color(color)
    ax.spines[side].set_linewidth(LW_AXES_SPINE)


def finish(fig):
    """Einheitliche Achsen-Box fuer alle Abbildungen."""
    fig.subplots_adjust(left=PAD_LEFT, right=PAD_RIGHT,
                        top=PAD_TOP, bottom=PAD_BOTTOM)
    plt.show()


def thicken_legend(leg, mew=6.5):
    handles = getattr(leg, 'legend_handles',
                      getattr(leg, 'legendHandles', leg.get_lines()))
    for h in handles:
        if hasattr(h, 'get_marker') and h.get_marker() not in ["None", "none", "", None]:
            h.set_markeredgewidth(mew)


###------------------------------------------------------------------------------------------###
### --------------------------- UMRECHNUNGEN ----------------------------------------------- ###
###------------------------------------------------------------------------------------------###

# Kontur
nozzle_x_mm = [x * 1000.0 for x in kontur_x_m] if kontur_x_m else []
nozzle_r_mm = [rv * 1000.0 for rv in kontur_r_m] if kontur_r_m else []

# Eingelesene Twg-Messpunkte
x_parsed_mm = [d['Location'] for d in daten]
twg         = [d['Temp_Twg'] for d in daten]

# Berechnete Verlaeufe
x_calc_hin_mm   = [x * 1000.0 for x in x_hin]
x_calc_rueck_mm = [x * 1000.0 for x in x_rueck] if 'x_rueck' in locals() else []

# Heat Flux: x-Werte stammen aus derselben Datei wie q -> immer konsistent
x_q_mm      = [x * 1000.0 for x in parsed_x_m]
q_parsed_mw = [qv / 1000.0 for qv in parsed_q_kw]      # kW/m^2 -> MW/m^2

# Druck und Fluidtemperatur (eingelesen)
x_p_read_mm = [x * 1000.0 for x in p_x_m] if p_x_m else []
x_T_read_mm = [x * 1000.0 for x in T_fluid_x_m] if T_fluid_x_m else []

# Kanalgeometrie: JEDE Groesse mit ihren EIGENEN x-Werten
x_hk_mm = [x * 1000.0 for x in kanal_xh_m] if kanal_xh_m else []
hk_mm   = [h * 1000.0 for h in kanal_h_m]  if kanal_h_m  else []

x_bk_mm = [x * 1000.0 for x in kanal_xb_m] if kanal_xb_m else []
bk_mm   = [b * 1000.0 for b in kanal_b_m]  if kanal_b_m  else []

if kanal_s_m:
    x_s_mm = [x * 1000.0 for x in kanal_xs_m]
    s_mm   = [sv * 1000.0 for sv in kanal_s_m]
else:
    # Fallback: konstante Wandstaerke aus Abschnitt 2
    x_s_mm = [0.0, max(nozzle_x_mm) if nozzle_x_mm else 1.0]
    s_mm   = [s * 1000.0, s * 1000.0]

# Farben
color_ti      = "#D90429"   # Twg
color_q       = "#8338ec"   # Waermestromdichte
color_contour = "#000000"   # Duesenkontur
color_T_fluid = "#0e6ba8"   # Fluidtemperatur
color_p       = "#000000"   # Druck
color_err     = "#003F88"   # Relativer Fehler
color_hk      = "#1ac9b4"
color_bk      = "#0a1045"
color_s       = "#d91770"

# Gemeinsame X-Grenze fuer ALLE Plots
MAX_X_VAL = max(nozzle_x_mm) if nozzle_x_mm else max(x_calc_hin_mm)


###------------------------------------------------------------------------------------------###
### ------------------ PLOT 1: WANDTEMPERATUR Twg & WAERMESTROMDICHTE q -------------------- ###
###------------------------------------------------------------------------------------------###

fig1, ax1 = plt.subplots(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))
lines_1 = []

# --- Achse 1: Temperatur ---
if x_parsed_mm:
    ln, = ax1.plot(x_parsed_mm, twg, marker="o", markerfacecolor="none",
                   ls="None", color=color_ti, ms=6.0, mew=2, zorder=4,
                   label=r"$T_{wg}$ (eingelesen nach Pizzarelli et al.)")
    lines_1.append(ln)

x_max_gueltig_mm = max(parsed_x_m) * 1000.0
_maske_calc = np.array(x_calc_hin_mm) <= x_max_gueltig_mm
x_calc_plot  = np.array(x_calc_hin_mm)[_maske_calc]
Twg_calc_plot = np.array(Twg_hin)[_maske_calc]

ln, = ax1.plot(x_calc_plot, Twg_calc_plot, color=color_ti, ls="-",
               lw=LW_CALC, zorder=3, label=r"$T_{wg}$ (berechnet)")
lines_1.append(ln)

if Laufrichtung == "Doppelstrom" and len(x_calc_rueck_mm) > 0:
    ln, = ax1.plot(x_calc_rueck_mm, Twg_rueck, color=color_ti, ls=":",
                   lw=LW_CALC, zorder=3, label=r"$T_{wg}$ Rück (berechnet)")
    lines_1.append(ln)

ax1.set_xlabel("Axiale Position [mm]", fontsize=FS_AXIS_LABEL, labelpad=12)
ax1.set_ylabel("Temperatur [K]", fontsize=FS_AXIS_LABEL, color=color_ti, labelpad=12)
ax1.tick_params(axis="x", colors=COLOR_AXES, labelsize=FS_TICK_LABEL,
                length=8, width=LW_TICKS)
style_axis(ax1, color_ti, "left")
ax1.set_xlim(0, MAX_X_VAL)
set_y_ticks(ax1, *YLIM_P1_TEMP)

# --- Achse 2: Waermestromdichte ---
ax1b = ax1.twinx()
ln, = ax1b.plot(x_q_mm, q_parsed_mw, marker="o", markerfacecolor="none",
                ls="None", color=color_q, ms=6.0, mew=2, zorder=4,
                label=r"$\dot{q}$ (eingelesen nach Pizzarelli et al.)")
lines_1.append(ln)

ax1b.set_ylabel(r"Wärmestromdichte $\left[\mathrm{MW/m^2}\right]$",
                fontsize=FS_AXIS_LABEL, color=color_q, labelpad=12)
style_axis(ax1b, color_q, "right")
set_y_ticks(ax1b, *YLIM_P1_Q)

# --- Achse 3: Duesenkontur (nur Formhinweis, keine Beschriftung) ---
if nozzle_x_mm:
    ax1c = ax1.twinx()
    ln, = ax1c.plot(nozzle_x_mm, nozzle_r_mm, color=color_contour, ls="-",
                    lw=4.5, zorder=1,
                    label=r"Düsenkontur (eingelesen nach Pizzarelli et al.)")
    lines_1.append(ln)
    ax1c.set_ylim(0, 250)
    ax1c.axis("off")

ax1.grid(True, linestyle="--", alpha=0.6, color=COLOR_GRID)
ax1.set_axisbelow(True)


def order_p1(line):
    lbl = line.get_label()
    if "$T_{wg}$ (eingelesen" in lbl: return 1
    if "$q$ (eingelesen" in lbl:      return 2
    if "Düsenkontur" in lbl:          return 3
    if "$T_{wg}$ (Berechnet)" in lbl: return 4
    if "$T_{wg}$ Rück" in lbl:        return 5
    return 6


sorted_1 = sorted(lines_1, key=order_p1)
leg1 = ax1.legend(sorted_1, [ln.get_label() for ln in sorted_1],
                  loc="upper left", bbox_to_anchor=(0.01, 0.99),
                  frameon=True, facecolor='white', framealpha=0.9,
                  fontsize=FS_LEGEND, markerscale=2.5)
thicken_legend(leg1)
finish(fig1)


###------------------------------------------------------------------------------------------###
### ------------------ PLOT 2: FLUID-TEMPERATUR UND DRUCK ---------------------------------- ###
###------------------------------------------------------------------------------------------###

fig2, ax2 = plt.subplots(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))
lines_2 = []

# --- Achse 1: Fluidtemperatur ---
if T_fluid_val_k and x_T_read_mm:
    ln, = ax2.plot(x_T_read_mm, T_fluid_val_k, marker="o", markerfacecolor="none",
                   ls="None", color=color_T_fluid, ms=6.0, mew=2, zorder=5,
                   label=r"$T_{co}$ (eingelesen nach Pizzarelli et al.)")
    lines_2.append(ln)

ln, = ax2.plot(x_calc_hin_mm, Tco_hin, color=color_T_fluid, ls="-",
               lw=LW_CALC, zorder=4, label=r"$T_{co}$ (berechnet)")
lines_2.append(ln)

if Laufrichtung == "Doppelstrom" and len(x_calc_rueck_mm) > 0:
    ln, = ax2.plot(x_calc_rueck_mm, Tco_rueck, color=color_T_fluid, ls=":",
                   lw=LW_CALC, zorder=4, label=r"$T_{co}$ Rück (berechnet)")
    lines_2.append(ln)

ax2.set_xlabel("Axiale Position [mm]", fontsize=FS_AXIS_LABEL, labelpad=12)
ax2.set_ylabel("Fluid-Temperatur [K]", fontsize=FS_AXIS_LABEL,
               color=color_T_fluid, labelpad=12)
ax2.tick_params(axis="x", colors=COLOR_AXES, labelsize=FS_TICK_LABEL,
                length=8, width=LW_TICKS)
style_axis(ax2, color_T_fluid, "left")
ax2.set_xlim(0, MAX_X_VAL)
set_y_ticks(ax2, *YLIM_P2_TEMP)

# --- Achse 2: Druck ---
ax2b = ax2.twinx()

if p_val_p and x_p_read_mm:
    ln, = ax2b.plot(x_p_read_mm, p_val_p, marker="o", markerfacecolor="none",
                    ls="None", color=color_p, ms=6.0, mew=2, zorder=3,
                    label=r"$p_{tot}$ (eingelesen nach Pizzarelli et al.)")
    lines_2.append(ln)

ln, = ax2b.plot(x_calc_hin_mm, p_hin, color=color_p, ls="-",
                lw=LW_CALC, zorder=2, label=r"$p$ (berechnet)")
lines_2.append(ln)

if Laufrichtung == "Doppelstrom" and len(x_calc_rueck_mm) > 0:
    ln, = ax2b.plot(x_calc_rueck_mm, p_rueck, color=color_p, ls="-.",
                    lw=LW_CALC, zorder=2, label=r"$p$ Rück (berechnet)")
    lines_2.append(ln)

ax2b.set_ylabel("Druck [bar]", fontsize=FS_AXIS_LABEL, color=color_p, labelpad=12)
style_axis(ax2b, color_p, "right")
set_y_ticks(ax2b, *YLIM_P2_P)

ax2.grid(True, linestyle="--", alpha=0.6, color=COLOR_GRID)
ax2.set_axisbelow(True)


def order_p2(line):
    lbl = line.get_label()
    if "$T_{co}$ (eingelesen" in lbl: return 1
    if "$p$ (eingelesen" in lbl:      return 2
    if "$T_{co}$ (Berechnet)" in lbl: return 3
    if "$T_{co}$ Rück" in lbl:        return 4
    if "$p$ (Berechnet)" in lbl:      return 5
    if "$p$ Rück" in lbl:             return 6
    return 7


sorted_2 = sorted(lines_2, key=order_p2)
leg2 = ax2.legend(sorted_2, [ln.get_label() for ln in sorted_2],
                  loc="upper left", bbox_to_anchor=(0.01, 0.99),
                  frameon=True, facecolor='white', framealpha=0.9,
                  fontsize=FS_LEGEND, markerscale=2.5)
thicken_legend(leg2)
finish(fig2)


###------------------------------------------------------------------------------------------###
### ----------- PLOT 33: KANALGEOMETRIE (HOEHE, BREITE, D_H & WANDDICKE S) ------------------ ###
###------------------------------------------------------------------------------------------###

fig4, ax4 = plt.subplots(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))
lines_4 = []

# WICHTIG: jede Groesse gegen IHRE eingelesenen x-Werte plotten
if len(hk_mm) > 0:
    ln, = ax4.plot(x_hk_mm, hk_mm, color=color_hk, marker="o", ls="None",
                   ms=9.0, mew=2.0, markerfacecolor="none",
                   label=r"Kanalhöhe $h_k(x)$ (eingelesen nach Pizzarelli et al.)")
    lines_4.append(ln)

if len(bk_mm) > 0:
    ln, = ax4.plot(x_bk_mm, bk_mm, color=color_bk, marker="o", ls="None",
                   ms=9.0, mew=2.0, markerfacecolor="none",
                   label=r"Kanalbreite $b_k(x)$ (eingelesen nach Pizzarelli et al.)")
    lines_4.append(ln)

if len(s_mm) > 0:
    ln, = ax4.plot(x_s_mm, s_mm, color=color_s, marker="o", ls="None",
                   ms=9.0, mew=2.0, markerfacecolor="none",
                   label=r"Wandstärke $s(x)$ (eingelesen nach Pizzarelli et al.)")
    lines_4.append(ln)

ax4.set_xlabel("Axiale Position [mm]", fontsize=FS_AXIS_LABEL, labelpad=12)
ax4.set_ylabel("Abmessung [mm]", fontsize=FS_AXIS_LABEL, color=COLOR_AXES, labelpad=12)
ax4.tick_params(axis="x", colors=COLOR_AXES, labelsize=FS_TICK_LABEL,
                length=8, width=LW_TICKS)
style_axis(ax4, COLOR_AXES, "left")
ax4.set_xlim(0, MAX_X_VAL)

set_y_ticks(ax4, *YLIM_P4_GEO)

# Kontrollausgabe, falls Werte ausserhalb der eingestellten Grenzen liegen
alle_werte = hk_mm + bk_mm + s_mm
if alle_werte and max(alle_werte) > YLIM_P4_GEO[1]:
    print(f"HINWEIS: groesste Abmessung {max(alle_werte):.3f} mm > "
          f"{YLIM_P4_GEO[1]} mm -> YLIM_P4_GEO anpassen.")

ax4.grid(True, linestyle="--", alpha=0.6, color=COLOR_GRID)
ax4.set_axisbelow(True)

if lines_4:
    leg4 = ax4.legend(lines_4, [ln.get_label() for ln in lines_4],
                      loc="upper left", bbox_to_anchor=(0.01, 0.99),
                      frameon=True, facecolor='white', framealpha=0.9,
                      fontsize=FS_LEGEND, markerscale=2.5)
    thicken_legend(leg4)

finish(fig4)


###------------------------------------------------------------------------------------------###
### ------------------ PLOT 4: SPEZIFISCHE WAERMEKAPAZITAET c_p ENTLANG DES KANALS -------- ###
###------------------------------------------------------------------------------------------###

YLIM_P5_CP = (0.0, 6.0)          # Plot 5: spez. Waermekapazitaet c_p     [kJ/(kg K)]
color_cp   = "#000000"

# c_p aus den gespeicherten Zustaenden (Tco in K, p in bar -> Pa)
cp_hin_kJ = [CP.PropsSI('C', 'T', T, 'P', pb * 1e5, fluid) / 1000.0
             for T, pb in zip(Tco_hin, p_hin)]

cp_rueck_kJ = []
if Laufrichtung == "Doppelstrom" and len(x_calc_rueck_mm) > 0:
    cp_rueck_kJ = [CP.PropsSI('C', 'T', T, 'P', pb * 1e5, fluid) / 1000.0
                   for T, pb in zip(Tco_rueck, p_rueck)]

fig5, ax5 = plt.subplots(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))
lines_5 = []

ln, = ax5.plot(x_calc_hin_mm, cp_hin_kJ, color=color_cp, ls="-",
               lw=LW_CALC, zorder=4, label=r"$c_p$ bei Bulktemperatur $T_{co}$ (berechnet)")
lines_5.append(ln)

if cp_rueck_kJ:
    ln, = ax5.plot(x_calc_rueck_mm, cp_rueck_kJ, color=color_cp, ls=":",
                   lw=LW_CALC, zorder=4, label=r"$c_p$ Rück (berechnet)")
    lines_5.append(ln)

ax5.set_xlabel("Axiale Position [mm]", fontsize=FS_AXIS_LABEL, labelpad=12)
ax5.set_ylabel(r"$c_p$ $\left[\mathrm{kJ/(kg\,K)}\right]$", fontsize=FS_AXIS_LABEL,
               color=color_cp, labelpad=12)
ax5.tick_params(axis="x", colors=COLOR_AXES, labelsize=FS_TICK_LABEL,
                length=8, width=LW_TICKS)
style_axis(ax5, color_cp, "left")
ax5.set_xlim(0, MAX_X_VAL)

set_y_ticks(ax5, *YLIM_P5_CP)

# Kontrollausgabe, falls Werte ausserhalb der eingestellten Grenzen liegen
alle_cp = cp_hin_kJ + cp_rueck_kJ
if alle_cp and (min(alle_cp) < YLIM_P5_CP[0] or max(alle_cp) > YLIM_P5_CP[1]):
    print(f"HINWEIS: c_p reicht von {min(alle_cp):.3f} bis {max(alle_cp):.3f} "
          f"kJ/(kg K) -> YLIM_P5_CP anpassen.")

ax5.grid(True, linestyle="--", alpha=0.6, color=COLOR_GRID)
ax5.set_axisbelow(True)

leg5 = ax5.legend(lines_5, [ln.get_label() for ln in lines_5],
                  loc="upper left", bbox_to_anchor=(0.01, 0.99),
                  frameon=True, facecolor='white', framealpha=0.9,
                  fontsize=FS_LEGEND, markerscale=2.5)
thicken_legend(leg5)
finish(fig5)