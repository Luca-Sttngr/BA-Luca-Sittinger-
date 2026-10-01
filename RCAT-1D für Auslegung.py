import os
import math
import numpy as np
import CoolProp.CoolProp as CP
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

###------------------------------------------------------------------------------------------###
### ------------------ 0. DATEN EINLESEN (Minimaler Parser ohne Output) -------------------- ###
###------------------------------------------------------------------------------------------###
dateipfad = r"" 
daten = []

if os.path.exists(dateipfad):
    with open(dateipfad, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    daten.append({
                        'Location': float(parts[0]),          # x [mm]
                        'Kontur': float(parts[1]),            # r [mm]au
                        'Total_Heat_Flux': float(parts[2]),   # q [kW/m^2]
                    })
                except ValueError:
                    pass   # faengt Kopfzeile, Trennlinie und "q_cuzr1.txt" ab
else:
    raise FileNotFoundError(dateipfad)

print(f"{len(daten)} Datenpunkte eingelesen")
# Umrechnung für den Rechencode: mm -> m
parsed_x_m = [d['Location'] / 1000.0 for d in daten]
parsed_q_kw = [d['Total_Heat_Flux'] for d in daten]


kontur_x_m = [d['Location'] / 1000.0 for d in daten]
kontur_r_m = [d['Kontur'] / 1000.0 for d in daten]


###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 1 Kühlmediumseigenschaften---------------------------###
###------------------------------------------------------------------------------------------###

fluid = "Ethanol"
rho = CP.PropsSI('D', 'T', 293.15, 'P', 60e5, fluid)                                  # Kühlmedium 
p = 60e5                                            # Druck des Kühlmediums bei Eintritt             [Pa] 
Tco = 288.15                                         # Temperatur des Kühlmediums bei Eintritt        [K] 
m_dot = 47.64e-3                                    # gesamter Kühlmediumsmassestrom                 [kg/s]
dx = 1e-3                                           # Länge der einzelnen Kontrollvolumina           [m]
h_fluid = CP.PropsSI('H', 'T', Tco, 'P', p, fluid)   # Enthalpie des Kühlmedium                       [J/kg] 
h_fluid_start = h_fluid
T_LIMIT_PROPS = 1200.0 
f_Nu_Auslegung = 1

###------------------------------------------------------------------------------------------###
### --------------------------Abschnitt 2 Brennkammereigenschaften-------------------------- ###
###------------------------------------------------------------------------------------------###

λWand = 310                                         # Wärmeleitfähigkeit Brennkammermaterial         [W/m*K]
s =  1e-3                                           # Wandstärke Brennkammer                         [m]                                       
Ra = 9.5e-6
ks =200e-6
# Universelle Konturgrenzen
x_injektor = 0.0                                    # Konturbeginn an der Injektorplatte             [m]
x_duesenende = max(kontur_x_m)                      # Konturende der Düse                            [m]
# Konfiguration der Durchströmungsrichtung und Rauigkeit
Laufrichtung = "Doppelstrom"                        # Auswahl: "Gegenstrom" oder "Doppelstrom"
Rauheit = "Rau"                                     # Auswahl: "Glatt" oder "Rau"

# Brennkammerinnenkontur (aus Datenpunkten) #
def r(x):
    """Innenradius. Ausserhalb des Datenbereichs werden die Randwerte gehalten."""
    return np.interp(x, kontur_x_m, kontur_r_m)


###------------------------------------------------------------------------------------------###
### --------------------------Abschnitt 3 Kanalgeometrie------------------------------------ ###
###------------------------------------------------------------------------------------------###

# Bei Gegenstrom n_rueck auf 0 setzen
n_hin    = 8
n_rueck  = 16
n_gesamt = n_hin + n_rueck


# --- Charakteristische Konturpositionen ---
i_throat   = int(np.argmin(kontur_r_m[:-1]))
x_throat   = kontur_x_m[i_throat]            # Duesenhals                      [m]
x_zyl_ende = 0.06                            # Ende des zylindrischen Teils    [m]
eps_throat = 2.0e-3                          # Aufweitungslaenge nach dem Hals [m]


# --- Stuetzstellen Hinweg (aufsteigend in x) ---
#     Injektor        Zylinderende    Hals            Duesenende
x_hin_stuetz = [x_injektor,     x_zyl_ende,     x_throat,       x_duesenende ]
b_hin_stuetz = [2.4e-3,        2.6e-3,           0.8e-3,         2.4e-3       ]
h_hin_stuetz = [0.8e-3,         0.8e-3,         1e-3,             0.8e-3       ]


#Gegenstrom
#x_hin_stuetz = [x_injektor,     x_zyl_ende,     x_throat,       x_duesenende ]
#b_hin_stuetz = [2.0e-3,         1.6e-3,          0.6e-3,         0.9e-3       ]
#h_hin_stuetz = [0.8e-3,         0.8e-3,         0.8e-3,             0.8e-3    ]


# --- Stuetzstellen Rueckweg (aufsteigend in x) ---
#     Injektor        Zylinderende    Hals            Duesenende
x_rueck_stuetz = [x_injektor,   x_zyl_ende,     x_throat,       x_duesenende ]
b_rueck_stuetz = [2e-3,       1.8e-3,         0.6e-3,         1.4e-3 ]
h_rueck_stuetz = [0.7e-3,       0.7e-3,       0.8e-3,         0.8e-3]

# --- Geglaettete Geometriefunktionen ---
x_glatt = np.linspace(x_injektor, x_duesenende, 2000)
fenster = 81                                  # ungerade, groesser = staerkere Rundung

def _glaetten(werte, n):
    rand = n // 2
    erw  = np.concatenate([np.full(rand, werte[0]), werte, np.full(rand, werte[-1])])
    return np.convolve(erw, np.ones(n) / n, mode="valid")

b_hin_glatt   = _glaetten(np.interp(x_glatt, x_hin_stuetz,   b_hin_stuetz),   fenster)
h_hin_glatt   = _glaetten(np.interp(x_glatt, x_hin_stuetz,   h_hin_stuetz),   fenster)
b_rueck_glatt = _glaetten(np.interp(x_glatt, x_rueck_stuetz, b_rueck_stuetz), fenster)
h_rueck_glatt = _glaetten(np.interp(x_glatt, x_rueck_stuetz, h_rueck_stuetz), fenster)

def b_hin(x):
    return float(np.interp(float(x), x_glatt, b_hin_glatt))

def h_hin(x):
    return float(np.interp(float(x), x_glatt, h_hin_glatt))

def b_rueck(x):
    return float(np.interp(float(x), x_glatt, b_rueck_glatt))

def h_rueck(x):
    return float(np.interp(float(x), x_glatt, h_rueck_glatt))


# --- Durchgangsdefinition ---
if Laufrichtung == "Doppelstrom":
    n_steps_doppelstrom = max(1, round((x_duesenende - x_injektor) / dx))
    dx_eff_doppelstrom = (x_duesenende - x_injektor) / n_steps_doppelstrom

    durchgaenge = [
        ("Hinweg",  x_injektor,   dx_eff_doppelstrom,
         x_duesenende + dx_eff_doppelstrom / 2,
         b_hin,   h_hin,   ks, n_hin),
        ("Rückweg", x_duesenende, -dx_eff_doppelstrom,
         x_injektor - dx_eff_doppelstrom / 2,
         b_rueck, h_rueck, ks, n_rueck)
    ]

elif Laufrichtung == "Gegenstrom":
    # Reine Gegenstromfuehrung: ein Durchgang vom Duesenende zum Injektor
    n_steps_doppelstrom = max(1, round((x_duesenende - x_injektor) / dx))
    dx_eff_doppelstrom = (x_duesenende - x_injektor) / n_steps_doppelstrom

    durchgaenge = [
        ("Gegenstrom", x_duesenende, -dx_eff_doppelstrom,
         x_injektor - dx_eff_doppelstrom / 2,
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
    return np.interp(x, q_data_x, q_data_q) * 1000.0    # kW/m^2 -> W/m^2

###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 5 Speicher fürs Plotten anlegen----------------------###
###------------------------------------------------------------------------------------------###

x_hin, Tco_hin, Tfsat_hin, Twc_hin, Twg_hin, p_hin = [], [], [], [], [], []
rho_hin, Re_hin, Nu_hin = [], [], []
q_hin, alpha_hin, c_hin = [], [], []
Re_lambda_hin = []
x_rueck, Tco_rueck, Tfsat_rueck, Twc_rueck, Twg_rueck, p_rueck = [], [], [], [], [], []
rho_rueck, Re_rueck, Nu_rueck = [], [], []
q_rueck, alpha_rueck, c_rueck = [], [], []
Re_lambda_rueck = []


###------------------------------------------------------------------------------------------###
###---------------------------Abschnitt 6,7 und 8 Berechnungschleife-------------------------###
###------------------------------------------------------------------------------------------###

# Gültigkeitsbereiche nach Kapitel 3
CHEN_KSD_MIN, CHEN_KSD_MAX = 5e-7, 40e-2    #5e-2  Korrekter Wert                 # Chen, Gleichung 
CHEN_RE_MIN,  CHEN_RE_MAX  =2e3, 4e8        #4e3,  4e8  Korrekter Wert
STIMPSON_RAD_MIN           = 0.0028                                               # Stimpson, Gleichung 
NORRIS_PR_MAX, NORRIS_XI_MAX = 6.0, 2.5                                           # Norris, Gleichung
GNIELINSKI_PR_MIN,GNIELINSKI_PR_MAX = 0.5, 2000                                   # Gnielinski, Gleichung
GNIELINSKI_RE_MIN,GNIELINSKI_RE_MAX = 2300, 1e6                                  

for typ, x_start, dx_schritt, x_end, b_input, h_input, ks_vorgabe, n_kanal in durchgaenge:
    x = x_start
    while (dx_schritt > 0 and x <= x_end) or (dx_schritt < 0 and x >= x_end):


            #6.1 Lokale Geometrie
            b_kanal = b_input(x) if callable(b_input) else b_input                # Kanalbreite
            h_kanal = h_input(x) if callable(h_input) else h_input                # Kanalhöhe
            A_Kanal       = b_kanal * h_kanal                                     # Querschnittsfläche Kanal
            d_hydraulisch = (4 * A_Kanal) / (2 * (b_kanal + h_kanal))             # hydraulischer Durchmesser
            m_dot_kanal   = m_dot / n_kanal                                       # Massestrom pro Kanal


            # 6.2 Stoffgrößen
            rho_bulk    = CP.PropsSI('D', 'H', h_fluid, 'P', p, fluid)            # mittlere Dichte
            cp_bulk     = CP.PropsSI('C', 'H', h_fluid, 'P', p, fluid)            # spezifische Wärmekapazität
            lambda_bulk = CP.PropsSI('L', 'H', h_fluid, 'P', p, fluid)            # Wärmeleitfähigkeit
            eta_bulk    = CP.PropsSI('V', 'H', h_fluid, 'P', p, fluid)            # dynamische Viskosität
            nu_bulk     = eta_bulk / rho_bulk                                     # kinematische Viskosität
            c_mittel    = m_dot_kanal / (rho_bulk * A_Kanal)                      # mittlere Kanalgeschwindigkeit
            Re          = (d_hydraulisch * c_mittel) / nu_bulk                    # Reynoldszahl
            Pr_bulk     = (nu_bulk * rho_bulk * cp_bulk) / lambda_bulk            # Prandtlzahl
            T_sat       = CP.PropsSI('T', 'P', p, 'Q', 0, fluid)                  # Siedetemperatur          


            # 6.3 Stoffgrößen
            q_lokal       = float(q(x))


            if Rauheit == "Rau":
                if Ra / d_hydraulisch <= STIMPSON_RAD_MIN:
                    print(f"Abbruch bei Stimpson-Korrelation. Außerhalb des Gültigkeitsbereichs bei x = {x*1000:.2f} mm")
                    break
                else:
                    # Stimpson-Korrelation
                    ks = 18 * Ra - 0.05 * d_hydraulisch
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


            # 6.5 Nusselt-Zahl
            if GNIELINSKI_RE_MIN <= Re <= GNIELINSKI_RE_MAX and GNIELINSKI_PR_MIN <= Pr_bulk <= GNIELINSKI_PR_MAX:
                #Gnielinski Korrelation
                ξ_glatt =  (1.8 * math.log10(Re) - 1.5)**-2
                Nu_Basis = (((ξ_glatt / 8) * (Re - 1000) * Pr_bulk) / ((1 + 12.7 * math.sqrt(ξ_glatt / 8) * (Pr_bulk**(2/3) - 1))))  * f_Nu_Auslegung   


            # 6.6 Rauheitskorrektur
            if Rauheit == "Rau":
                 ξ_norris = ξ_chen / ξ_glatt
                 if ξ_norris < 1.0:
                    print(f"Keine Verstärkung des Wärmeübergangs bei x = {x*1000:.2f} mm")
                    break
                 else:
                # Norris Gleichung begrenzen 
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
            alpha_Kühlrippenkorrektur = alpha_konv * (b_kanal + 2 * η_Kühlrippe * h_kanal) / (b_kanal + steg_breite)     # Koorektur Wärmeübergangskoeffizient


###---------------------------Abschnitt 7 Energieerhaltung und Wandtemperaturen------------------------###

            # 7.1 Effektive Querschnittsfläche
            A_umfang = 2 * math.pi * float(r(x)) * abs(dx_schritt)
            if Laufrichtung == "Doppelstrom":
                teilung_hin   = b_hin(x)   + steg_breite
                teilung_rueck = b_rueck(x) + steg_breite
                U_belegt = n_hin * teilung_hin + n_rueck * teilung_rueck
                teilung  = teilung_hin if typ == "Hinweg" else teilung_rueck
                A_eff    = A_umfang * teilung / U_belegt
            else:
                A_eff = A_umfang / n_kanal

            # 7.2 Wandtemperatur auf Kühlkanalseite
            Twc = Tco + (q_lokal / alpha_Kühlrippenkorrektur)

            # 7.3 Wandtemperatur auf Heißgasseite
            Twg = Twc + ((q_lokal * s) / λWand)
        
            # 7.4 Energieerhaltung
            h_fluid = h_fluid + ((q_lokal * A_eff) / m_dot_kanal)  

            # 7.5 Neue Fluidtemperatur aus Coolprop abfragen
            try:
                Tco = CP.PropsSI('T', 'H', h_fluid, 'P', p, fluid)
            except:
                print(f"Abbruch: Austrittszustand außerhalb der Stoffdatenbank "f"bei x = {x*1000:.2f} mm")
                break
    

            ###---------------------------Abschnitt 9 Werte abspeichern----------------------------------###

            if typ in ["Gleichstrom", "Gegenstrom", "Hinweg"]:
                x_hin.append(x)
                Tco_hin.append(Tco)
                Twc_hin.append(Twc)
                Twg_hin.append(Twg)
                Tfsat_hin.append(T_sat)
                p_hin.append(p / 1e5)
                rho_hin.append(rho_bulk)
                Re_hin.append(Re)
                Nu_hin.append(Nu)
                q_hin.append(q_lokal)
                alpha_hin.append(alpha_Kühlrippenkorrektur)
                c_hin.append(c_mittel)
                Re_lambda_hin.append((Re,  ξ_druckverlust))
            else:                                                           # Rückweg bei Doppelstrom
                x_rueck.append(x)
                Tco_rueck.append(Tco)
                Twc_rueck.append(Twc)
                Twg_rueck.append(Twg)
                Tfsat_rueck.append(T_sat)
                p_rueck.append(p / 1e5)
                rho_rueck.append(rho_bulk)
                Re_rueck.append(Re)
                Nu_rueck.append(Nu)
                q_rueck.append(q_lokal)
                alpha_rueck.append(alpha_Kühlrippenkorrektur)
                c_rueck.append(c_mittel)
                Re_lambda_rueck.append((Re,  ξ_druckverlust))

            x = x + dx_schritt

###------------------------------------------------------------------------------------------###
### --------------------------- ENERGIEBILANZ-VERIFIKATION --------------------------------- ###
###------------------------------------------------------------------------------------------###
Q_kuehlmittel = m_dot * (h_fluid - h_fluid_start)          # [W]

x_fein = np.linspace(x_injektor, x_duesenende, 5000)
Q_heissgas = np.trapz(q(x_fein) * 2 * np.pi * r(x_fein), x_fein)   # [W]

rel_fehler = (Q_kuehlmittel - Q_heissgas) / Q_heissgas * 100

print(f"Q_Kühlmittel (Enthalpiebilanz):     {Q_kuehlmittel/1000:8.3f} kW")
print(f"Q_Heißgas   (Flächenintegral q(x)): {Q_heissgas/1000:8.3f} kW")
print(f"Relative Abweichung:                {rel_fehler:8.2f} %")



# ==============================================================================
# 1. GLOBALES STYLING
# ==============================================================================

FIG_WIDTH_IN, FIG_HEIGHT_IN = 15, 17
LW_DATA, LW_CALC, LW_AXES_SPINE = 9, 9, 2.25
LW_CONTOUR = 4.5
LW_GRID, LW_TICKS = 1.2, 2.0
TICK_LENGTH = 8
LABEL_PAD = 12
COLOR_GRID, COLOR_AXES = "#B0B0B0", "#333333"

FS_AXIS_LABEL = 48
FS_TICK_LABEL = 46
FS_LEGEND     = 40

LEGEND_LOC     = "upper left"
LEGEND_ANCHOR  = (0.0005, 0.9995)
TIGHT_LAYOUT   = dict(pad=0.6, w_pad=0.2, h_pad=0.6)
X_TICK_STEP_MM = 25.0
KONTUR_YLIM    = (0, 120)      # Skalierung der ausgeblendeten Konturachse
X_LABEL        = "Axiale Position [mm]"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": FS_TICK_LABEL,
    "axes.titlesize": FS_AXIS_LABEL,
    "axes.labelsize": FS_AXIS_LABEL,
    "xtick.labelsize": FS_TICK_LABEL,
    "ytick.labelsize": FS_TICK_LABEL,
    "legend.fontsize": FS_LEGEND,
    "legend.handlelength": 1.5,
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


# ==============================================================================
# 2. FARBEN
# ==============================================================================

color_ti      = "#D90429"   # Heissgaswandtemperatur
color_twc     = "#fb8600be" # Kuehlkanalwandtemperatur
color_q       = "#8338ec"   # Waermestromdichte
color_contour = "#000000"   # Duesenkontur
color_T_fluid = "#0e6ba8"   # Fluidtemperatur
color_p       = "#000000"   # Druck
color_tsat    = "#2a9d8f"   # Siedetemperatur
color_rho     = "#e07a5f"   # Dichte
color_re      = "#3d405b"   # Reynoldszahl
color_alpha   = "#9e0059"   # Waermeuebergangskoeffizient
color_c       = "#008000"   # Fluidgeschwindigkeit
color_b       = "#118ab2"   # Kanalbreite
color_h       = "#4b9d45"   # Kanalhoehe
color_steg    = "#000000"   # Stegbreite
color_s       = "#ef476f"   # Wandstaerke


# ==============================================================================
# 3. UMRECHNUNGEN & GEMEINSAME X-ACHSE
# ==============================================================================

nozzle_x_mm     = [x * 1000.0 for x in kontur_x_m]
nozzle_r_mm     = [r * 1000.0 for r in kontur_r_m]
x_calc_hin_mm   = [x * 1000.0 for x in x_hin]
x_calc_rueck_mm = [x * 1000.0 for x in x_rueck]
x_geo_mm        = np.array(x_calc_hin_mm)

X_MAX_MM   = max(nozzle_x_mm) if len(nozzle_x_mm) > 0 else max(x_calc_hin_mm)
X_TICKS_MM = np.arange(0.0, X_MAX_MM, X_TICK_STEP_MM)

HAT_RUECK   = len(x_rueck) > 0
DOPPELSTROM = (Laufrichtung == "Doppelstrom") and HAT_RUECK


def runde_ab(wert, schritt):
    return math.floor(wert / schritt) * schritt


def runde_auf(wert, schritt):
    return math.ceil(wert / schritt) * schritt


def serie(x, y, label, color, ls="-", lw=LW_CALC, zorder=4):
    """Eine Datenreihe fuer make_plot."""
    return {"x": x, "y": y, "label": label, "color": color,
            "ls": ls, "lw": lw, "zorder": zorder}


KONTUR_SERIE = [
    serie(nozzle_x_mm, nozzle_r_mm, r"Düsenkontur $r(x)$",
          color_contour, ls="-", lw=LW_CONTOUR, zorder=1),
]


# ==============================================================================
# 4. UNIVERSELLE PLOT-FUNKTION (Format = Plot Fluidgeschwindigkeit)
# ==============================================================================

def make_plot(y1, y1_label, y1_color, y1_lim, y1_ticks,
              y2=None, y2_label="", y2_color=COLOR_AXES,
              y2_lim=None, y2_ticks=None,
              kontur=False, x_label=X_LABEL):

    fig, ax1 = plt.subplots(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))
    all_lines = []

    def _draw(ax, series_list):
        drawn = []
        for ser in series_list:
            x_data = ser["x"]
            if x_data is None or len(x_data) == 0:
                continue
            line, = ax.plot(
                x_data, ser["y"],
                marker="None",
                linestyle=ser["ls"],
                color=ser["color"],
                linewidth=ser["lw"],
                label=ser["label"],
                zorder=ser["zorder"],
            )
            drawn.append(line)
        return drawn

    # ---------- Achse 1 (links) ----------
    all_lines.extend(_draw(ax1, y1))
    ax1.set_xlabel(x_label, fontsize=FS_AXIS_LABEL, labelpad=LABEL_PAD)
    ax1.set_ylabel(y1_label, fontsize=FS_AXIS_LABEL, color=y1_color, labelpad=LABEL_PAD)
    ax1.tick_params(axis="both", labelsize=FS_TICK_LABEL, length=TICK_LENGTH, width=LW_TICKS)
    ax1.tick_params(axis="y", colors=y1_color)
    ax1.spines["left"].set_color(y1_color)
    ax1.spines["left"].set_linewidth(LW_AXES_SPINE)

    ax1.set_xlim(0, X_MAX_MM)
    ax1.set_xticks(X_TICKS_MM)
    ax1.set_ylim(y1_lim)
    ax1.set_yticks(y1_ticks)

    # ---------- Achse 2 (rechts) ----------
    if y2:
        ax2 = ax1.twinx()
        all_lines.extend(_draw(ax2, y2))
        ax2.set_ylabel(y2_label, fontsize=FS_AXIS_LABEL, color=y2_color, labelpad=LABEL_PAD)
        ax2.tick_params(axis="y", colors=y2_color, labelsize=FS_TICK_LABEL,
                        length=TICK_LENGTH, width=LW_TICKS)
        ax2.spines["right"].set_linewidth(LW_AXES_SPINE)
        ax2.spines["right"].set_color(y2_color)
        if y2_lim is not None:
            ax2.set_ylim(y2_lim)
        if y2_ticks is not None:
            ax2.set_yticks(y2_ticks)

    # ---------- Achse 3: Duesenkontur (ausgeblendet) ----------
    if kontur:
        ax3 = ax1.twinx()
        all_lines.extend(_draw(ax3, KONTUR_SERIE))
        ax3.set_ylim(KONTUR_YLIM)
        ax3.axis("off")

    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.set_axisbelow(True)

    if all_lines:
        ax1.legend(
            all_lines, [ln.get_label() for ln in all_lines],
            loc=LEGEND_LOC, bbox_to_anchor=LEGEND_ANCHOR,
            frameon=True, facecolor="white", framealpha=0.9,
            fontsize=FS_LEGEND,
        )

    plt.tight_layout(**TIGHT_LAYOUT)
    plt.show()


# ==============================================================================
# PLOT 1: WANDTEMPERATUREN & WAERMESTROMDICHTE
# ==============================================================================

y1_plot1 = [
    serie(x_calc_hin_mm, Twg_hin, r"$T_{wg}$ Gleichstrom", color_ti,  "-", zorder=4),
    serie(x_calc_hin_mm, Twc_hin, r"$T_{wc}$ Gleichstrom", color_twc, "-", zorder=3),
]
if DOPPELSTROM:
    y1_plot1 += [
        serie(x_calc_rueck_mm, Twg_rueck, r"$T_{wg}$ Gegenstrom", color_ti,  ":", zorder=4),
        serie(x_calc_rueck_mm, Twc_rueck, r"$T_{wc}$ Gegenstrom", color_twc, ":", zorder=3),
    ]

y2_plot1 = [
    serie(x_calc_hin_mm, [qv / 1e6 for qv in q_hin], r"$q$", color_q, "-", zorder=2),
]

make_plot(
    y1=y1_plot1,
    y1_label="Temperatur [K]",
    y1_color=color_ti,
    y1_lim=(0, 1000),
    y1_ticks=np.linspace(0, 1000, 6),
    #y2=y2_plot1,
    #y2_label=r"Wärmestromdichte $\left[\mathrm{MW/m^2}\right]$",
    #y2_color=color_q,
    y2_lim=(0, 25),
    y2_ticks=np.linspace(0, 25, 6),
)


# ==============================================================================
# PLOT 2: FLUIDGESCHWINDIGKEIT UND DRUCK  (Referenzformat)
# ==============================================================================

y1_plot4 = [
    serie(x_calc_hin_mm, c_hin, r"$c_{m}$ Gleichstrom", color_c, "-", zorder=4),
]
if DOPPELSTROM:
    y1_plot4.append(
        serie(x_calc_rueck_mm, c_rueck, r"$c_{m}$ Gegenstrom", color_c, ":", zorder=4)
    )

y2_plot4 = [
    serie(x_calc_hin_mm, p_hin, r"$p$ Gleichstrom", color_p, "-", zorder=3),
]
if DOPPELSTROM:
    y2_plot4.append(
        serie(x_calc_rueck_mm, p_rueck, r"$p$ Gegenstrom", color_p, ":", zorder=3)
    )

make_plot(
    y1=y1_plot4,
    y1_label=r"Fluidgeschwindigkeit $\left[\mathrm{m/s}\right]$",
    y1_color=color_c,
    y1_lim=(0, 15),
    y1_ticks=np.linspace(0, 15, 6),
    y2=y2_plot4,
    y2_label="Druck [bar]",
    y2_color=color_p,
    y2_lim=(50, 65),
    y2_ticks=np.linspace(50, 65, 6),
)


# ==============================================================================
# PLOT 3: WAERMEUEBERGANGSKOEFFIZIENT UND BRENNKAMMERRADIUS
# ==============================================================================

y1_plot5 = [
    serie(x_calc_hin_mm, [a / 1000.0 for a in alpha_hin],
          r"$\alpha$ Gleichstrom", color_alpha, "-", zorder=4),
]
if DOPPELSTROM:
    y1_plot5.append(
        serie(x_calc_rueck_mm, [a / 1000.0 for a in alpha_rueck],
              r"$\alpha$ Gegenstrom", color_alpha, ":", zorder=4)
    )

y2_plot5 = [
    serie(nozzle_x_mm, nozzle_r_mm, r"$r(x)$", color_contour, "-", zorder=4),
]

alle_al = [a / 1000.0 for a in alpha_hin] + \
          ([a / 1000.0 for a in alpha_rueck] if HAT_RUECK else [])
al_hi = runde_auf(max(alle_al), 5.0)

make_plot(
    y1=y1_plot5,
    y1_label=r"$\alpha$ $\left[\mathrm{kW/(m^2\,K)}\right]$",
    y1_color=color_alpha,
    y1_lim=(0, al_hi),
    y1_ticks=np.linspace(0, al_hi, 6),
    y2=y2_plot5,
    y2_label="Brennkammerradius [mm]",
    y2_color=color_contour,
    y2_lim=(0, 100),
    y2_ticks=np.linspace(0, 100, 6),
)
