"""Product records for the RM proposals. Every maker_quote was read on maker_url on 2026-11-24 (see maker_checked).
No prices anywhere (the maker pages show them; they are deliberately not copied). Render look-alikes are labelled."""

MARAZZI_GML = "https://www.marazzigroup.com/collections/grande-marble-look-collection/"
STONE_TAFU = dict(
    maker="Marazzi", range="Grande Marble Look", name="Tafu Lux RT", code="MEP6",
    colour_or_finish="Tafu, Lux (polished), rectified; taupe-grey marble look with white veining",
    format_mm={"w": 1200, "l": 2780, "t": 6.5},
    maker_url=MARAZZI_GML, maker_quote="GRANDE MARBLE LOOK TAFU LUX RT Size: 120x278cm Code: MEP6 Technology: Colorbody fine porcelain stoneware Thickness: MM 6,5",
    colour_source="maker swatch image grande-marble-look-mep6 (mean linear 0.406/0.338/0.269)",
    label="look-alike-proxy", lookalike="ambientCG Marble007 (CC0), colour-matched to the maker swatch",
    consistent_with="Marazzi Mystone Gris Fleury Taupe floor chosen 2026-11-23 (same maker, taupe family)")
STONE_FRAPPUCCINO = dict(
    maker="Marazzi", range="Grande Marble Look", name="Frappuccino Rettificato Lux", code="M0G3",
    colour_or_finish="Frappuccino, Lux, rectified; dark brown marble look with pale veining",
    format_mm={"w": 1200, "l": 1200, "t": 6.5},
    maker_url=MARAZZI_GML, maker_quote="GRANDE MARBLE LOOK FRAPPUCCINO RETTIFICATO LUX Size: 120x120cm Code: M0G3 Technology: Colorbody fine porcelain stoneware Thickness: MM 6,5",
    colour_source="maker swatch image grande-marble-look-m0g3 (mean linear 0.082/0.055/0.039)",
    label="look-alike-proxy", lookalike="ambientCG Marble007 (CC0), colour-matched to the maker swatch",
    consistent_with="the client's chosen wet-room wall tile (Frappuccino), so the same stone runs from the ensuite to the cinema")
SLATS_WALNUT = dict(
    maker="WoodUpp", range="Akupanel (Natural Wood)", name="Akupanel Acoustic Panel, Natural Wood, Walnut, Black Felt, 240 x 60 cm",
    colour_or_finish="Walnut veneer slats on black felt",
    format_mm={"w": 600, "l": 2400},
    maker_url="https://woodupp.com/products/akupanel-acoustic-panel-natural-wood-walnut-black-felt-240-x-60-cm",
    maker_quote="Akupanel | Acoustic Panel Natural Wood, Walnut, Black Felt, 240 x 60 cm",
    colour_source="maker product name (walnut veneer); slat width and pitch are NOT on the page text and are not claimed",
    label="look-alike-proxy", lookalike="scene 'walnut' material (EGGER H3180 look-alike, CC0 Wood051)",
    consistent_with="reads as the client's chosen Brown Halifax / walnut joinery; acoustic benefit for the cinema")
BROWN_HALIFAX = dict(
    maker="EGGER", range="Feelwood", name="H3180 ST37 Brown Halifax Oak", code="H3180 ST37",
    colour_or_finish="Brown Halifax Oak, ST37 (dark brown woodgrain)",
    maker_url="https://www.egger.com/en/furniture-interior-design/decors/H3180_37?country=GB",
    maker_quote="The dark brown colour of H3180 Brown Halifax Oak meets the trend for dark woodgrain decors and is reminiscent in terms of colour of the colonial style.",
    colour_source="chosen.json joinery-timber (client palette C, 2026-11-23)",
    label="look-alike-proxy", lookalike="scene 'walnut' material", consistent_with="the client's chosen parents' bedroom joinery")
BOCCI_28 = dict(
    maker="Bocci", range="28 Series (cluster)", name="28.19 Cluster, Clear", code="28.19",
    colour_or_finish="Clear hand-blown glass",
    maker_url="https://bocci.com/shop/products/28-19-cluster/",
    maker_quote="28.19 is composed of 19 hand-blown glass pendants that attach using a connector to a single cluster canopy. Colour Options Clear",
    colour_source="maker product page, Colour Options: Clear",
    label="look-alike-proxy", lookalike="clear glass globes with an emissive core; number of globes in the mock-up (5) is NOT the maker's 19",
    note="the maker also sells the series as single pendants and a configurator for custom installations; confirm a 5-globe canopy with Bocci",
    consistent_with="clear blown-glass globe clusters in references 19, 28 and 31")
FLOS_IC = dict(
    maker="Flos", range="IC Lights", name="IC Lights S1 (Suspension 1), Brass", code="F3175059",
    colour_or_finish="Brass frame, blown opal glass diffuser",
    maker_url="https://flos.com/en/gb/ic-lights-suspension/M-ic-lights-suspension.html",
    maker_quote="Suspension lamp emitting diffused light. Features a metal frame available in brushed and transparent varnished brass, chrome-plated steel or black, with a blown opal glass diffuser.",
    colour_source="maker page, Color: Brass",
    label="look-alike-proxy", lookalike="emissive opal sphere", consistent_with="opal globe pendants low over the nightstands in reference 5, brass accents in the brief")
GRIS_FLEURY = dict(
    maker="Marazzi", range="Mystone Gris Fleury", name="Gris Fleury Taupe RT 60x120", code="MLGY",
    colour_or_finish="Taupe, matt, rectified, through-body coloured porcelain",
    format_mm={"w": 600, "l": 1200, "t": 10},
    maker_url="https://www.marazzi.it/en/mystone-gris-fleury",
    maker_quote="GRIS FLEURY TAUPE RT Formato: 60x120cm Codice: MLGY Tecnologia: Gres fine porcellanato colorato in massa",
    colour_source="chosen.json floor-basement (client palette C, 2026-11-23)",
    label="look-alike-proxy", lookalike="ambientCG Marble007 (CC0), as the floor", consistent_with="the client's chosen basement floor, carried up the dining wall")
