"""Large English test dataset for ProjectIQ (Test environment): 50 customers, 30 suppliers with contacts and
compliance documents, 54 items with supplier prices, 18 resources with costs and absences, 23 projects of eleven types
in every status (Offer, In Progress, Suspended, Closed) with WBS, dependencies, allocations, baselines, time entries in
every status, material usage, purchasing (requests, RFQs, orders, receipts, supplier invoices) and a project timeline
(notes, tasks, phone calls, appointments).

All names, addresses, VAT numbers and IBANs are fictitious (phone numbers in the reserved +44 20 7946 0xxx range,
e-mail domains under the reserved .example top-level domain, IBANs with the invalid check digits 00). The data is
generated with a fixed random seed and dates relative to today, so every run gives the same picture.

Running again deletes the previous test data first; `--clean` only deletes it. Uses the PAC_* environment variables
(point PAC_ENVIRONMENT_URL at the target environment). The project manager and their resource are linked to the first
interactive user (or SEED_USER_EMAIL), so that user sees the timesheet, the approvals and the timeline.
"""
import datetime as dt, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

R = {'Prefer': 'return=representation'}
TODAY = dt.date.today()
MONDAY = TODAY - dt.timedelta(days=TODAY.weekday())
rnd = random.Random(365)
WORKERS = 6


def D(days):
    return (TODAY + dt.timedelta(days=days)).isoformat()


def call(method, url, **kw):
    for attempt in range(6):
        r = S.request(method, API + url, **kw)
        if r.status_code in (429, 502, 503, 504) or (r.status_code == 500 and any(
                w in r.text.lower() for w in ('deadlock', 'timeout', 'try again'))):
            time.sleep(int(r.headers.get('Retry-After', 2 ** attempt)))
            continue
        return r
    return r


def get(q):
    out, url = [], q
    while url:
        body = call('GET', url, headers={'Prefer': 'odata.maxpagesize=500'}).json()
        out += body.get('value', [])
        url = body.get('@odata.nextLink', '').replace(API, '') or None
    return out


def post(es, body):
    r = call('POST', es, json=body, headers=R)
    if r.status_code >= 300:
        raise SystemExit(f'{es}: {r.status_code} {r.text[:400]}')
    return r.json()


def patch(es, body, strict=True):
    r = call('PATCH', es, json=body)
    if r.status_code >= 300 and strict:
        raise SystemExit(f'{es}: {r.status_code} {r.text[:400]}')
    return r.status_code < 300


def action(name, body=None, strict=True):
    r = call('POST', name, json=body or {})
    if r.status_code >= 300:
        if strict:
            raise SystemExit(f'{name}: {r.status_code} {r.text[:400]}')
        print('  warning:', name.split('.')[-1], r.status_code, r.json().get('error', {}).get('message', '')[:160])
        return None
    return r.json() if r.text else {}


def bound(es, id_, name, body=None, strict=True):
    return action(f'{es}({id_})/Microsoft.Dynamics.CRM.{name}', body, strict)


def parallel(fn, items):
    with ThreadPoolExecutor(WORKERS) as pool:
        return list(pool.map(fn, items))


def bind(table, id_):
    return f'/{table}({id_})'


# ====================================================================================================================
# Master data
# ====================================================================================================================
# name, industry, city, country, customer type
CUSTOMERS = [
    ('Riverside Estates Ltd', 'Real estate', 'London', 'GB', 'Customer'),
    ('Northgate Retail Group', 'Retail', 'Manchester', 'GB', 'Customer'),
    ('Harbour Hotels plc', 'Hospitality', 'Liverpool', 'GB', 'Customer'),
    ('Greenfield Foods Ltd', 'Food & beverage', 'Leeds', 'GB', 'Customer'),
    ('Bluewave Logistics', 'Logistics', 'Bristol', 'GB', 'Customer'),
    ('Crestline Pharmaceuticals', 'Pharmaceuticals', 'Milan', 'IT', 'Customer'),
    ('Summit Data Centres', 'IT services', 'Dublin', 'IE', 'Customer'),
    ('Oakridge Manufacturing', 'Manufacturing', 'Birmingham', 'GB', 'Customer'),
    ('Silverline Beverages', 'Food & beverage', 'Turin', 'IT', 'Customer'),
    ('St Clement Medical Centre', 'Healthcare', 'Edinburgh', 'GB', 'Customer'),
    ('Westbrook University', 'Education', 'Cardiff', 'GB', 'Customer'),
    ('Ironbridge Automotive', 'Automotive', 'Coventry', 'GB', 'Customer'),
    ('Maple Leaf Supermarkets', 'Retail', 'Glasgow', 'GB', 'Customer'),
    ('Pinecrest Office Parks', 'Real estate', 'Reading', 'GB', 'Customer'),
    ('Cobalt Packaging Solutions', 'Manufacturing', 'Bologna', 'IT', 'Customer'),
    ('Lighthouse Public Schools Trust', 'Education', 'Plymouth', 'GB', 'Customer'),
    ('Granite City Bank', 'Financial services', 'Aberdeen', 'GB', 'Customer'),
    ('Falcon Distribution Centre', 'Logistics', 'Northampton', 'GB', 'Customer'),
    ('Evergreen Care Homes', 'Healthcare', 'Norwich', 'GB', 'Customer'),
    ('Sterling Chemicals', 'Chemicals', 'Rotterdam', 'NL', 'Customer'),
    ('Kingsway Shopping Centre', 'Retail', 'Sheffield', 'GB', 'Customer'),
    ('Aurora Hotels & Resorts', 'Hospitality', 'Rome', 'IT', 'Customer'),
    ('Meridian Plastics', 'Manufacturing', 'Brescia', 'IT', 'Customer'),
    ('Thornbury Council', 'Public sector', 'Bath', 'GB', 'Customer'),
    ('Copperfield Brewing Co', 'Food & beverage', 'Cork', 'IE', 'Customer'),
    ('Atlas Cold Storage', 'Logistics', 'Southampton', 'GB', 'Customer'),
    ('Brightwater Leisure Centres', 'Leisure', 'Nottingham', 'GB', 'Customer'),
    ('Redwood Furniture Works', 'Manufacturing', 'Leicester', 'GB', 'Customer'),
    ('Harlow Business Park', 'Real estate', 'Cambridge', 'GB', 'Customer'),
    ('Seaview Marina', 'Leisure', 'Brighton', 'GB', 'Customer'),
    ('Orion Telecom', 'Telecommunications', 'Milan', 'IT', 'Customer'),
    ('Willow Creek Dairy', 'Food & beverage', 'Exeter', 'GB', 'Customer'),
    ('Beacon Hill Hospital', 'Healthcare', 'Newcastle', 'GB', 'Customer'),
    ('Quarry Lane Cement', 'Construction materials', 'Derby', 'GB', 'Customer'),
    ('Nova Biotech Labs', 'Pharmaceuticals', 'Oxford', 'GB', 'Customer'),
    ('Castlegate Car Parks', 'Transport', 'York', 'GB', 'Customer'),
    ('Elmstead Logistics Park', 'Logistics', 'Milton Keynes', 'GB', 'Customer'),
    ('Fairmont Textile Mills', 'Manufacturing', 'Prato', 'IT', 'Customer'),
    ('Horizon Airport Services', 'Transport', 'Belfast', 'GB', 'Customer'),
    ('Juniper Wellness Spa', 'Hospitality', 'Harrogate', 'GB', 'Customer'),
    ('Kestrel Engineering', 'Manufacturing', 'Swindon', 'GB', 'Prospect'),
    ('Lakeside Conference Centre', 'Hospitality', 'Windermere', 'GB', 'Prospect'),
    ('Moorland Water Services', 'Utilities', 'Bradford', 'GB', 'Prospect'),
    ('Northern Light Studios', 'Media', 'Salford', 'GB', 'Prospect'),
    ('Old Mill Apartments', 'Real estate', 'Chester', 'GB', 'Prospect'),
    ('Primrose Garden Centres', 'Retail', 'Canterbury', 'GB', 'Prospect'),
    ('Quayside Fisheries', 'Food & beverage', 'Grimsby', 'GB', 'Prospect'),
    ('Rosewood Private School', 'Education', 'Cheltenham', 'GB', 'Prospect'),
    ('Tidewater Ferries', 'Transport', 'Portsmouth', 'GB', 'Prospect'),
    ('Valley Fresh Bakeries', 'Food & beverage', 'Florence', 'IT', 'Prospect'),
]
# name, category, city, country, blocked
SUPPLIERS = [
    ('Volt Electrical Wholesale', 'Electrical', 'Birmingham', 'GB', False),
    ('Sparkline Cables Ltd', 'Electrical', 'Manchester', 'GB', False),
    ('PowerGrid Switchgear', 'Electrical', 'Milan', 'IT', False),
    ('BrightBeam Lighting', 'Lighting', 'Leeds', 'GB', False),
    ('Lumen Direct', 'Lighting', 'London', 'GB', False),
    ('SunPeak Solar Distribution', 'Solar', 'Bologna', 'IT', False),
    ('Helios Energy Supplies', 'Solar', 'Bristol', 'GB', False),
    ('ClimateCore HVAC', 'HVAC', 'Glasgow', 'GB', False),
    ('AirFlow Ducting Ltd', 'HVAC', 'Sheffield', 'GB', False),
    ('ThermaTech Heat Pumps', 'HVAC', 'Verona', 'IT', False),
    ('AquaPipe Plumbing Supplies', 'Plumbing', 'Nottingham', 'GB', False),
    ('FireGuard Systems', 'Fire safety', 'Leicester', 'GB', False),
    ('RedAlert Fire Protection', 'Fire safety', 'Dublin', 'IE', False),
    ('NetLink Distribution', 'Networking', 'Reading', 'GB', False),
    ('FibreOne Components', 'Networking', 'Cambridge', 'GB', False),
    ('Automa Controls', 'Automation', 'Turin', 'IT', False),
    ('LogicDrive Automation', 'Automation', 'Coventry', 'GB', False),
    ('Stonebridge Building Materials', 'Building materials', 'Derby', 'GB', False),
    ('DryWall Express', 'Building materials', 'Leeds', 'GB', False),
    ('Timberland Joinery Supplies', 'Building materials', 'Norwich', 'GB', False),
    ('ChargePoint Wholesale', 'EV charging', 'Milton Keynes', 'GB', False),
    ('E-Mobility Parts Co', 'EV charging', 'Munich', 'DE', False),
    ('SafeWork PPE', 'Safety', 'Liverpool', 'GB', False),
    ('ToolHire Pro', 'Equipment rental', 'Bristol', 'GB', False),
    ('LiftUp Access Platforms', 'Equipment rental', 'Swindon', 'GB', False),
    ('SteelForm Fabrications', 'Steel', 'Sheffield', 'GB', False),
    ('Concrete Solutions Ltd', 'Building materials', 'York', 'GB', False),
    ('QuickShip Logistics', 'Logistics', 'Northampton', 'GB', True),
    ('Budget Electrical Outlet', 'Electrical', 'Luton', 'GB', True),
    ('Cheapside Fixings', 'Building materials', 'Croydon', 'GB', True),
]
# code, name, category, unit, unit cost
ITEMS = [
    ('MAT-0001', 'Power cable 3G2.5 mm2', 'Electrical', 'm', 1.15),
    ('MAT-0002', 'Power cable 5G6 mm2', 'Electrical', 'm', 4.60),
    ('MAT-0003', 'Armoured cable SWA 4C 16 mm2', 'Electrical', 'm', 14.80),
    ('MAT-0004', 'Distribution board 24 ways', 'Electrical', 'pcs', 185.00),
    ('MAT-0005', 'Main switchboard 630 A', 'Electrical', 'pcs', 9800.00),
    ('MAT-0006', 'Miniature circuit breaker 16 A', 'Electrical', 'pcs', 6.40),
    ('MAT-0007', 'RCBO 32 A 30 mA', 'Electrical', 'pcs', 38.50),
    ('MAT-0008', 'Cable tray 300 mm galvanised', 'Electrical', 'm', 17.20),
    ('MAT-0009', 'PVC conduit 25 mm', 'Electrical', 'm', 1.40),
    ('MAT-0010', 'Socket outlet twin 13 A', 'Electrical', 'pcs', 7.90),
    ('MAT-0011', 'LED panel 600x600 40 W', 'Lighting', 'pcs', 32.00),
    ('MAT-0012', 'LED high bay 150 W', 'Lighting', 'pcs', 118.00),
    ('MAT-0013', 'LED downlight 12 W', 'Lighting', 'pcs', 14.50),
    ('MAT-0014', 'Emergency light 3 h', 'Lighting', 'pcs', 46.00),
    ('MAT-0015', 'DALI lighting controller', 'Lighting', 'pcs', 420.00),
    ('MAT-0016', 'Occupancy sensor', 'Lighting', 'pcs', 36.00),
    ('MAT-0017', 'PV module 450 W', 'Solar', 'pcs', 128.00),
    ('MAT-0018', 'String inverter 50 kW', 'Solar', 'pcs', 4250.00),
    ('MAT-0019', 'Hybrid inverter 10 kW', 'Solar', 'pcs', 1690.00),
    ('MAT-0020', 'PV mounting rail 4.2 m', 'Solar', 'pcs', 29.00),
    ('MAT-0021', 'Solar DC cable 6 mm2', 'Solar', 'm', 1.35),
    ('MAT-0022', 'Battery storage module 5 kWh', 'Solar', 'pcs', 2150.00),
    ('MAT-0023', 'Air-to-water heat pump 40 kW', 'HVAC', 'pcs', 14200.00),
    ('MAT-0024', 'Air-cooled chiller 120 kW', 'HVAC', 'pcs', 36500.00),
    ('MAT-0025', 'Fan coil unit 4-pipe', 'HVAC', 'pcs', 690.00),
    ('MAT-0026', 'Galvanised duct 400 mm', 'HVAC', 'm', 38.00),
    ('MAT-0027', 'Air handling unit 8000 m3/h', 'HVAC', 'pcs', 18900.00),
    ('MAT-0028', 'Ceiling diffuser 600x600', 'HVAC', 'pcs', 54.00),
    ('MAT-0029', 'Copper pipe 22 mm', 'Plumbing', 'm', 9.80),
    ('MAT-0030', 'Ball valve DN50', 'Plumbing', 'pcs', 48.00),
    ('MAT-0031', 'Pipe insulation 22 mm', 'Plumbing', 'm', 2.30),
    ('MAT-0032', 'Addressable smoke detector', 'Fire safety', 'pcs', 42.00),
    ('MAT-0033', 'Fire alarm control panel 4 loops', 'Fire safety', 'pcs', 3150.00),
    ('MAT-0034', 'Sprinkler head pendent', 'Fire safety', 'pcs', 11.50),
    ('MAT-0035', 'Steel sprinkler pipe DN65', 'Fire safety', 'm', 24.00),
    ('MAT-0036', 'Manual call point', 'Fire safety', 'pcs', 27.00),
    ('MAT-0037', 'Cat6A U/FTP cable', 'Networking', 'm', 0.95),
    ('MAT-0038', 'Single-mode fibre 24 core', 'Networking', 'm', 3.70),
    ('MAT-0039', 'Patch panel 24 ports Cat6A', 'Networking', 'pcs', 145.00),
    ('MAT-0040', 'Rack cabinet 42U', 'Networking', 'pcs', 980.00),
    ('MAT-0041', 'Access switch 48 ports PoE', 'Networking', 'pcs', 2450.00),
    ('MAT-0042', 'Wi-Fi 6 access point', 'Networking', 'pcs', 390.00),
    ('MAT-0043', 'PLC CPU module', 'Automation', 'pcs', 2850.00),
    ('MAT-0044', 'Digital I/O module 32 channels', 'Automation', 'pcs', 520.00),
    ('MAT-0045', 'HMI touch panel 15 in', 'Automation', 'pcs', 1890.00),
    ('MAT-0046', 'Variable frequency drive 22 kW', 'Automation', 'pcs', 1640.00),
    ('MAT-0047', 'Plasterboard 12.5 mm', 'Building materials', 'm2', 6.20),
    ('MAT-0048', 'Metal stud 50 mm', 'Building materials', 'm', 2.10),
    ('MAT-0049', 'Suspended ceiling tile 600x600', 'Building materials', 'm2', 11.40),
    ('MAT-0050', 'Ready-mix concrete C30', 'Building materials', 'm3', 118.00),
    ('MAT-0051', 'Vinyl floor covering', 'Building materials', 'm2', 24.50),
    ('MAT-0052', 'EV wallbox 22 kW', 'EV charging', 'pcs', 1180.00),
    ('MAT-0053', 'DC fast charger 150 kW', 'EV charging', 'pcs', 38500.00),
    ('MAT-0054', 'Safety harness kit', 'Safety', 'pcs', 165.00),
]
# key, name, role, hourly cost, weekly hours, working days (None = Monday-Friday)
RESOURCES = [
    ('site1', 'Oliver Bennett', 'Site manager', 48, 40, None),
    ('site2', 'Emma Clarke', 'Site manager', 47, 40, None),
    ('ele1', 'James Walker', 'Electrician', 32, 40, None),
    ('ele2', 'Sophie Turner', 'Electrician', 31, 40, None),
    ('ele3', 'Daniel Hughes', 'Electrician', 33, 40, None),
    ('ele4', 'Chloe Morgan', 'Electrician', 30, 40, None),
    ('hvac1', 'Ryan Cooper', 'HVAC technician', 34, 40, None),
    ('hvac2', 'Megan Price', 'HVAC technician', 33, 40, None),
    ('mason1', 'Thomas Reed', 'Builder', 28, 40, None),
    ('mason2', 'Harry Evans', 'Builder', 27, 40, None),
    ('carp1', 'Jack Simmons', 'Carpenter', 29, 40, None),
    ('eng1', 'Grace Mitchell', 'Design engineer', 45, 40, None),
    ('auto1', 'Lucas Hayes', 'Automation engineer', 46, 40, None),
    ('net1', 'Ethan Brooks', 'Network technician', 30, 40, None),
    ('net2', 'Isla Ward', 'Network technician', 30, 32, '365000000,365000001,365000002,365000003'),
    ('comm1', 'Amelia Foster', 'Commissioning technician', 36, 24, '365000000,365000002,365000004'),
    ('hse1', 'Noah Bailey', 'HSE officer', 40, 20, '365000001,365000003'),
]
ROLE_KEYS = {'site': ['site1', 'site2'], 'ele': ['ele1', 'ele2', 'ele3', 'ele4'], 'hvac': ['hvac1', 'hvac2'],
             'mason': ['mason1', 'mason2'], 'carp': ['carp1'], 'eng': ['eng1'], 'auto': ['auto1'], 'net': ['net1', 'net2'],
             'comm': ['comm1'], 'hse': ['hse1'], 'pm': ['pm']}
ABSENCES = [  # name, type (0 vacation, 1 leave, 2 sickness, 3 closure), resource key, from, to
    ('Summer holiday - James Walker', 0, 'ele1', -80, -66),
    ('Summer holiday - Ryan Cooper', 0, 'hvac1', -73, -60),
    ('Annual leave - Emma Clarke', 0, 'site2', 10, 14),
    ('Annual leave - Sophie Turner', 0, 'ele2', 24, 28),
    ('Sick leave - Harry Evans', 2, 'mason2', -9, -7),
    ('Medical appointment - Megan Price', 1, 'hvac2', -2, -2),
    ('Training course - Lucas Hayes', 1, 'auto1', 3, 4),
    ('Christmas holiday - Grace Mitchell', 0, 'eng1', 57, 64),
    ('Company closure - Christmas', 3, None, '2026-12-24', '2026-12-26'),
    ('Company closure - New Year', 3, None, '2027-01-01', '2027-01-01'),
    ('Company closure - Bank holiday', 3, None, '2026-08-31', '2026-08-31'),
]

# WBS templates: code, name, parent, start/end as fraction of the project, base hours, base materials, roles
TEMPLATES = {
    'renovation': [
        ('1', 'Site setup and demolition', None, None, None, 0, 0, []),
        ('1.1', 'Site setup', '1', 0.0, 0.06, 40, 1500, ['site']),
        ('1.2', 'Strip-out and demolition', '1', 0.06, 0.2, 160, 800, ['mason']),
        ('2', 'Building works', None, None, None, 0, 0, []),
        ('2.1', 'Partition walls and ceilings', '2', 0.2, 0.5, 280, 9000, ['mason', 'carp']),
        ('2.2', 'Flooring and decoration', '2', 0.5, 0.75, 160, 7000, ['carp']),
        ('3', 'Building services', None, None, None, 0, 0, []),
        ('3.1', 'Electrical and lighting', '3', 0.3, 0.7, 240, 8000, ['ele']),
        ('3.2', 'Heating and ventilation', '3', 0.35, 0.75, 200, 12000, ['hvac']),
        ('4', 'Snagging and handover', None, 0.75, 1.0, 80, 1000, ['site', 'hse']),
    ],
    'pv': [
        ('1', 'Design and grid application', None, 0.0, 0.2, 100, 0, ['eng', 'pm']),
        ('2', 'Installation', None, None, None, 0, 0, []),
        ('2.1', 'Mounting structures', '2', 0.2, 0.45, 200, 9000, ['ele', 'mason']),
        ('2.2', 'PV modules', '2', 0.4, 0.65, 180, 30000, ['ele']),
        ('2.3', 'Inverters and DC/AC wiring', '2', 0.6, 0.85, 150, 12000, ['ele']),
        ('3', 'Grid connection and commissioning', None, 0.85, 1.0, 60, 1500, ['comm', 'eng']),
    ],
    'electrical': [
        ('1', 'Survey and design', None, 0.0, 0.15, 60, 0, ['eng']),
        ('2', 'Main switchboard replacement', None, 0.15, 0.45, 180, 15000, ['ele']),
        ('3', 'Sub-distribution and wiring', None, 0.3, 0.8, 320, 11000, ['ele']),
        ('4', 'Lighting and small power', None, 0.6, 0.85, 120, 6000, ['ele']),
        ('5', 'Testing and certification', None, 0.85, 1.0, 50, 500, ['comm', 'hse']),
    ],
    'hvac': [
        ('1', 'Survey and heat load calculation', None, 0.0, 0.1, 40, 0, ['eng']),
        ('2', 'Removal of existing plant', None, 0.1, 0.25, 80, 500, ['hvac', 'mason']),
        ('3', 'New plant installation', None, None, None, 0, 0, []),
        ('3.1', 'Heat pumps and chillers', '3', 0.25, 0.55, 200, 38000, ['hvac']),
        ('3.2', 'Ductwork and terminals', '3', 0.35, 0.75, 240, 14000, ['hvac', 'carp']),
        ('3.3', 'Controls and BMS', '3', 0.6, 0.85, 100, 6000, ['auto']),
        ('4', 'Commissioning and balancing', None, 0.85, 1.0, 60, 0, ['comm', 'hvac']),
    ],
    'cabling': [
        ('1', 'Network design', None, 0.0, 0.15, 50, 0, ['eng', 'net']),
        ('2', 'Cabling', None, None, None, 0, 0, []),
        ('2.1', 'Cable trays and containment', '2', 0.15, 0.4, 120, 4000, ['ele']),
        ('2.2', 'Copper and fibre cabling', '2', 0.3, 0.7, 240, 9000, ['net']),
        ('3', 'Active equipment and Wi-Fi', None, 0.65, 0.9, 100, 18000, ['net']),
        ('4', 'Certification and documentation', None, 0.85, 1.0, 40, 0, ['net', 'comm']),
    ],
    'automation': [
        ('1', 'Functional specification', None, 0.0, 0.15, 80, 0, ['auto', 'eng']),
        ('2', 'Control panels', None, 0.15, 0.45, 200, 22000, ['ele']),
        ('3', 'PLC and HMI software', None, 0.2, 0.7, 320, 3000, ['auto']),
        ('4', 'On-site installation', None, 0.5, 0.8, 220, 5000, ['ele', 'auto']),
        ('5', 'FAT, SAT and operator training', None, 0.8, 1.0, 80, 0, ['auto', 'comm']),
    ],
    'fire': [
        ('1', 'Fire risk assessment and design', None, 0.0, 0.15, 50, 0, ['eng', 'hse']),
        ('2', 'Fire detection system', None, 0.15, 0.6, 200, 14000, ['ele']),
        ('3', 'Sprinkler system', None, 0.25, 0.75, 220, 26000, ['hvac']),
        ('4', 'Testing and fire authority approval', None, 0.8, 1.0, 50, 800, ['comm', 'hse']),
    ],
    'ev': [
        ('1', 'Load study and permits', None, 0.0, 0.25, 40, 0, ['eng']),
        ('2', 'Civil works and trenching', None, 0.2, 0.5, 120, 6000, ['mason']),
        ('3', 'Charger installation', None, 0.45, 0.8, 140, 42000, ['ele']),
        ('4', 'Commissioning and back-office setup', None, 0.8, 1.0, 40, 500, ['comm', 'net']),
    ],
    'led': [
        ('1', 'Lighting survey and design', None, 0.0, 0.1, 24, 0, ['eng']),
        ('2', 'Fixture replacement', None, 0.1, 0.8, 260, 28000, ['ele']),
        ('3', 'Lighting controls', None, 0.5, 0.9, 80, 7000, ['auto']),
        ('4', 'Handover and disposal certificates', None, 0.9, 1.0, 20, 0, ['ele', 'hse']),
    ],
    'maintenance': [
        ('1', 'Q1 planned maintenance', None, 0.0, 0.25, 120, 2000, ['hvac', 'ele']),
        ('2', 'Q2 planned maintenance', None, 0.25, 0.5, 120, 2000, ['hvac', 'ele']),
        ('3', 'Q3 planned maintenance', None, 0.5, 0.75, 120, 2000, ['hvac', 'ele']),
        ('4', 'Q4 planned maintenance', None, 0.75, 1.0, 120, 2000, ['hvac', 'ele']),
        ('5', 'Reactive maintenance call-outs', None, 0.0, 1.0, 160, 3000, ['ele']),
    ],
}
LINKS = {
    'renovation': [('1.1', '1.2'), ('1.2', '2.1'), ('2.1', '2.2'), ('2.2', '4'), ('3.1', '4'), ('3.2', '4')],
    'pv': [('1', '2.1'), ('2.1', '2.2'), ('2.2', '2.3'), ('2.3', '3')],
    'electrical': [('1', '2'), ('2', '4'), ('3', '5'), ('4', '5')],
    'hvac': [('1', '2'), ('2', '3.1'), ('3.1', '3.3'), ('3.2', '4'), ('3.3', '4')],
    'cabling': [('1', '2.1'), ('2.1', '2.2'), ('2.2', '4'), ('3', '4')],
    'automation': [('1', '2'), ('2', '4'), ('3', '5'), ('4', '5')],
    'fire': [('1', '2'), ('2', '4'), ('3', '4')],
    'ev': [('1', '2'), ('2', '3'), ('3', '4')],
    'led': [('1', '2'), ('2', '4'), ('3', '4')],
    'maintenance': [('1', '2'), ('2', '3'), ('3', '4')],
}
CATEGORIES = {'renovation': ['Building materials', 'Electrical', 'Lighting', 'HVAC'], 'pv': ['Solar', 'Electrical'],
              'electrical': ['Electrical', 'Lighting'], 'hvac': ['HVAC', 'Plumbing'], 'cabling': ['Networking', 'Electrical'],
              'automation': ['Automation', 'Electrical'], 'fire': ['Fire safety', 'Electrical'], 'ev': ['EV charging', 'Electrical'],
              'led': ['Lighting', 'Electrical'], 'maintenance': ['HVAC', 'Electrical', 'Plumbing']}
# name, type, customer index, status, start offset (days), duration (days), contract value
PROJECTS = [
    ('Head office refurbishment - Riverside Tower', 'renovation', 0, 'In Progress', -70, 160, 240000),
    ('Rooftop solar plant 450 kWp', 'pv', 3, 'In Progress', -50, 140, 380000),
    ('Main switchboard upgrade - Plant 2', 'electrical', 7, 'In Progress', -40, 90, 95000),
    ('HVAC replacement - Northgate Mall', 'hvac', 1, 'In Progress', -90, 180, 520000),
    ('Campus network refresh', 'cabling', 10, 'In Progress', -30, 100, 140000),
    ('Bottling line automation', 'automation', 8, 'In Progress', -60, 150, 310000),
    ('Fire protection upgrade - Logistics hub', 'fire', 4, 'In Progress', -45, 120, 185000),
    ('EV charging hub - 24 points', 'ev', 35, 'In Progress', -20, 90, 260000),
    ('LED retrofit - three warehouses', 'led', 17, 'In Progress', -35, 75, 120000),
    ('Facility maintenance 2026 - Harbour Hotels', 'maintenance', 2, 'In Progress', None, None, 90000),
    ('Ward B renovation - St Clement Medical Centre', 'renovation', 9, 'In Progress', -15, 120, 175000),
    ('Solar carport 120 kWp', 'pv', 13, 'In Progress', -100, 150, 160000),
    ('Data centre cooling upgrade', 'hvac', 6, 'Suspended', -80, 160, 410000),
    ('Store fit-out - Kingsway Shopping Centre', 'renovation', 20, 'Suspended', -60, 100, 85000),
    ('School LED retrofit', 'led', 15, 'Offer', 30, 60, 70000),
    ('Warehouse solar plant 1 MWp', 'pv', 25, 'Offer', 60, 200, 820000),
    ('Packaging line automation', 'automation', 14, 'Offer', 45, 160, 290000),
    ('Fire alarm upgrade - Pinecrest Office Parks', 'fire', 28, 'Offer', 20, 90, 110000),
    ('Hotel EV charging', 'ev', 21, 'Offer', 90, 60, 65000),
    ('Data room cabling - Granite City Bank', 'cabling', 16, 'Closed', -260, 80, 60000),
    ('Factory lighting retrofit', 'led', 27, 'Closed', -220, 70, 98000),
    ('Plant room HVAC refurbishment', 'hvac', 18, 'Closed', -330, 150, 270000),
    ('Substation switchboard replacement', 'electrical', 11, 'Closed', -200, 100, 130000),
]
STATUS = {'Offer': 365000000, 'In Progress': 1, 'Suspended': 365000001}
COUNTRY = {'GB': 'United Kingdom', 'IT': 'Italy', 'IE': 'Ireland', 'NL': 'Netherlands', 'DE': 'Germany'}
FIRST = ['Alice', 'Ben', 'Charlotte', 'David', 'Eleanor', 'Frank', 'Georgia', 'Henry', 'Imogen', 'Joshua', 'Katie', 'Liam',
         'Mia', 'Nathan', 'Olivia', 'Peter', 'Rachel', 'Samuel', 'Tara', 'William', 'Zoe', 'Adam', 'Bethany', 'Callum',
         'Daisy', 'Edward', 'Freya', 'George', 'Hannah', 'Isaac']
LAST = ['Adams', 'Baker', 'Carter', 'Dawson', 'Ellis', 'Fletcher', 'Gibson', 'Harris', 'Irving', 'Jenkins', 'Knight',
        'Lawson', 'Marshall', 'Newton', 'Owens', 'Parker', 'Quinn', 'Robinson', 'Shaw', 'Taylor', 'Underwood', 'Vaughan',
        'Watson', 'Young', 'Abbott', 'Barnes', 'Cole', 'Dixon', 'Fox', 'Grant']
JOBS = ['Facilities Manager', 'Operations Director', 'Procurement Manager', 'Technical Manager', 'Estates Manager',
        'Plant Manager', 'Finance Director', 'Head of Property']


def slug(name):
    return ''.join(c if c.isalnum() else '-' for c in name.lower()).replace('--', '-').strip('-')[:40]


def vat(country):
    return country + ''.join(str(rnd.randint(0, 9)) for _ in range(11 if country == 'IT' else 9))


def phone():
    return f'+44 20 7946 0{rnd.randint(0, 999):03d}'


# ====================================================================================================================
# Clean
# ====================================================================================================================
def delete(es, ids):
    """Deletes one by one (cascades on projects are heavy) and retries what failed; returns what is left."""
    for _ in range(3):
        left = []
        for i in ids:
            r = call('DELETE', f'{es}({i})')
            if r.status_code >= 300 and r.status_code != 404:
                left.append(i)
        if not left:
            return []
        ids = left
        time.sleep(5)
    print(f'  could not delete {len(ids)} {es}:', r.text[:200])
    return ids


def clean():
    names = {n for n, *_ in CUSTOMERS + SUPPLIERS}
    accounts = [a['accountid'] for a in get('accounts?$select=accountid,name') if a['name'] in names]
    ids = set(accounts)
    delete('op365_supplierinvoices', [i['op365_supplierinvoiceid'] for i in get('op365_supplierinvoices?$select=op365_supplierinvoiceid,_op365_supplierid_value')
                                      if i['_op365_supplierid_value'] in ids])
    titles = {n for n, *_ in PROJECTS}
    projects = [p['op365_projectid'] for p in get('op365_projects?$select=op365_projectid,op365_name,_op365_customerid_value')
                if p['_op365_customerid_value'] in ids or p['op365_name'] in titles]
    delete('op365_projects', projects)
    codes = {c for c, *_ in ITEMS}
    delete('op365_items', [i['op365_itemid'] for i in get('op365_items?$select=op365_itemid,op365_code') if i['op365_code'] in codes])
    absences = {n for n, *_ in ABSENCES}
    delete('op365_absences', [a['op365_absenceid'] for a in get('op365_absences?$select=op365_absenceid,op365_name') if a['op365_name'] in absences])
    people = {n for _, n, *_ in RESOURCES}
    delete('op365_resources', [r['op365_resourceid'] for r in get('op365_resources?$select=op365_resourceid,op365_name') if r['op365_name'] in people])
    delete('contacts', [c['contactid'] for c in get('contacts?$select=contactid,_parentcustomerid_value') if c['_parentcustomerid_value'] in ids])
    delete('accounts', accounts)
    print(f'test data deleted: {len(accounts)} accounts, {len(projects)} projects')

clean()
if '--clean' in sys.argv:
    sys.exit(0)

email = os.environ.get('SEED_USER_EMAIL')
users = get("systemusers?$select=systemuserid,fullname,internalemailaddress&$filter=isdisabled eq false and accessmode eq 0 "
            "and applicationid eq null" + (f" and internalemailaddress eq '{email}'" if email else ''))
user = users[0] if users else None
me = user['systemuserid'] if user else call('GET', 'WhoAmI').json()['UserId']
OWNER = {'ownerid@odata.bind': bind('systemusers', me)} if user else {}
print('seed user:', user['fullname'] if user else 'application user')

# ---------- customers ----------
acc, cust, supp = {}, [], {}


def customer(row):
    name, industry, city, country, kind = row
    body = {'name': name, 'op365_iscustomer': True, 'op365_customertype': 365000001 if kind == 'Customer' else 365000000,
            'op365_vatnumber': vat(country), 'telephone1': phone(), 'emailaddress1': f'info@{slug(name)}.example',
            'websiteurl': f'https://www.{slug(name)}.example', 'address1_line1': f'{rnd.randint(1, 250)} {rnd.choice(["High", "Station", "Church", "Mill", "Park", "Victoria", "King", "Queen"])} {rnd.choice(["Street", "Road", "Lane", "Avenue"])}',
            'address1_city': city, 'address1_postalcode': f'{rnd.randint(10000, 99999)}', 'address1_country': COUNTRY[country],
            'op365_language': 365000001, 'op365_paymentterms': rnd.choice(['30 days net', '60 days end of month', '90 days end of month']),
            'description': f'{industry} customer (test data).', **OWNER}
    contacts = [(rnd.choice(FIRST), rnd.choice(LAST), rnd.choice(JOBS), i == 0) for i in range(rnd.choice([1, 2, 2, 3]))]
    return name, body, contacts


for name, body, contacts in [customer(c) for c in CUSTOMERS]:
    acc[name] = body, contacts
rows = list(acc.items())


def create_account(row):
    name, (body, contacts) = row
    a = post('accounts', body)['accountid']
    for first, last, job, decision in contacts:
        post('contacts', {'firstname': first, 'lastname': last, 'jobtitle': job, 'op365_isdecisionmaker': decision,
                          'emailaddress1': f'{first.lower()}.{last.lower()}@{body["emailaddress1"].split("@")[1]}',
                          'telephone1': phone(), 'parentcustomerid_account@odata.bind': bind('accounts', a), **OWNER})
    return name, a


ids = dict(parallel(create_account, rows))
cust = [ids[c[0]] for c in CUSTOMERS]
print('customers:', len(cust))

# ---------- suppliers ----------
rows = []
for name, category, city, country, blocked in SUPPLIERS:
    body = {'name': name, 'op365_issupplier': True, 'op365_supplierstatus': 365000001 if blocked else 365000000,
            'op365_suppliercategory': category, 'op365_vatnumber': vat(country), 'telephone1': phone(),
            'emailaddress1': f'orders@{slug(name)}.example', 'op365_pec': f'admin@pec.{slug(name)}.example',
            'op365_iban': f'{country}00X' + ''.join(str(rnd.randint(0, 9)) for _ in range(22)),
            'op365_paymentterms': rnd.choice(['30 days net', '60 days end of month', '90 days end of month']),
            'websiteurl': f'https://www.{slug(name)}.example', 'address1_city': city, 'address1_country': COUNTRY[country],
            'address1_line1': f'Unit {rnd.randint(1, 40)}, {rnd.choice(["Enterprise", "Riverside", "Gateway", "Phoenix"])} Industrial Estate',
            'op365_language': 365000001, 'description': f'{category} supplier (test data).'
            + (' Blocked after repeated late deliveries.' if blocked else ''), **OWNER}
    rows.append((name, (body, [(rnd.choice(FIRST), rnd.choice(LAST), 'Sales Account Manager', True)])))
supp = dict(parallel(create_account, rows))
SUPP_BY_CAT = {}
for name, category, *_, blocked in SUPPLIERS:
    if not blocked:
        SUPP_BY_CAT.setdefault(category, []).append(supp[name])
print('suppliers:', len(supp))

docs = []
for name, *_ in SUPPLIERS:
    expiry = rnd.choice([-20, 10, 25, 60, 120, 200, 300])
    docs.append({'op365_description': f'DURC - {name}', 'op365_documenttype': 365000000, 'op365_number': f'INAIL_{rnd.randint(10**7, 10**8)}',
                 'op365_issuedate': D(expiry - 120), 'op365_expirydate': D(expiry), 'op365_SupplierId@odata.bind': bind('accounts', supp[name])})
    docs.append({'op365_description': f'Public liability insurance - {name}', 'op365_documenttype': 365000003,
                 'op365_number': f'POL-{rnd.randint(100000, 999999)}', 'op365_issuedate': D(-200), 'op365_expirydate': D(rnd.choice([-5, 165, 300])),
                 'op365_SupplierId@odata.bind': bind('accounts', supp[name])})
parallel(lambda b: post('op365_supplierdocuments', b), docs)

# ---------- items ----------
ITEM = {}


def create_item(row):
    code, name, category, uom, cost = row
    r = random.Random(code)
    suppliers = SUPP_BY_CAT.get(category) or SUPP_BY_CAT['Electrical']
    chosen = r.sample(suppliers, min(len(suppliers), r.choice([1, 2, 2, 3])))
    i = post('op365_items', {'op365_code': code, 'op365_name': name, 'op365_category': category, 'op365_uom': uom,
                             'op365_unitcost': cost, 'op365_DefaultSupplierId@odata.bind': bind('accounts', chosen[0]), **OWNER})['op365_itemid']
    for n, s in enumerate(chosen):
        post('op365_itemsuppliers', {'op365_ItemId@odata.bind': bind('op365_items', i), 'op365_SupplierId@odata.bind': bind('accounts', s),
                                     'op365_price': round(cost * r.uniform(0.88, 1.02), 2), 'op365_leadtimedays': r.choice([2, 5, 7, 10, 15, 30]),
                                     'op365_suppliercode': f'{code[-4:]}-{r.randint(100, 999)}',
                                     'op365_minimumlot': 1 if uom == 'pcs' else r.choice([50, 100])})
    return code, (i, chosen, category, uom, cost, name)


ITEM = dict(parallel(create_item, ITEMS))
print('items:', len(ITEM))

# ---------- resources ----------
RES, COST = {}, {}
mine = get(f'op365_resources?$select=op365_resourceid,op365_name&$filter=_op365_userid_value eq {me}') if user else []
if mine:
    RES['pm'] = mine[0]['op365_resourceid']
else:
    body = {'op365_name': user['fullname'] if user else 'Project Manager', 'op365_role': 'Project manager', 'op365_weeklyhours': 40}
    if user:
        body['op365_UserId@odata.bind'] = bind('systemusers', me)
    RES['pm'] = post('op365_resources', body)['op365_resourceid']
if not get(f"op365_resourcecosts?$select=op365_resourcecostid&$filter=_op365_resourceid_value eq {RES['pm']}"):
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': bind('op365_resources', RES['pm']), 'op365_validfrom': '2025-01-01',
                                 'op365_hourlycost': 58})
COST['pm'] = 58
WORKDAYS = {'pm': {0, 1, 2, 3, 4}}
for key, name, role, cost, hours, days in RESOURCES:
    body = {'op365_name': name, 'op365_role': role, 'op365_weeklyhours': hours, **OWNER}
    if days:
        body['op365_workingdays'] = days
    r = post('op365_resources', body)['op365_resourceid']
    RES[key], COST[key] = r, cost
    WORKDAYS[key] = {int(d) - 365000000 for d in days.split(',')} if days else {0, 1, 2, 3, 4}
    # a cost increase on 1 January keeps two history rows
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': bind('op365_resources', r), 'op365_validfrom': '2025-01-01',
                                 'op365_hourlycost': round(cost * 0.96, 2)})
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': bind('op365_resources', r), 'op365_validfrom': '2026-01-01',
                                 'op365_hourlycost': cost})
OFF = set()
for name, kind, who, start, end in ABSENCES:
    s = D(start) if isinstance(start, int) else start
    e = D(end) if isinstance(end, int) else end
    body = {'op365_name': name, 'op365_absencetype': 365000000 + kind, 'op365_fromdate': s, 'op365_todate': e}
    if who:
        body['op365_ResourceId@odata.bind'] = bind('op365_resources', RES[who])
    post('op365_absences', body)
    d = dt.date.fromisoformat(s)
    while d <= dt.date.fromisoformat(e):
        OFF.add((who, d))
        d += dt.timedelta(days=1)
print('resources:', len(RES))


# ====================================================================================================================
# Projects
# ====================================================================================================================
def day(offset):
    return TODAY + dt.timedelta(days=offset)


class P:
    pass


def build_project(n_row):
    n, (name, kind, ci, status, start, duration, value) = n_row
    r = random.Random(n)
    p = P()
    p.name, p.kind, p.status, p.value, p.customer, p.customer_name = name, kind, status, value, cust[ci], CUSTOMERS[ci][0]
    if start is None:  # yearly contract
        p.start, p.end = dt.date(TODAY.year, 1, 1), dt.date(TODAY.year, 12, 31)
    else:
        p.start, p.end = day(start), day(start + duration)
    p.stop = TODAY - dt.timedelta(days=r.randint(18, 30)) if status == 'Suspended' else TODAY
    span = (p.end - p.start).days
    # budget at about 80% of the contract value (labour at an average 37/h)
    scale = 0.8 * value / sum(h * 37 + m * 1.03 for *_, h, m, _ in TEMPLATES[kind])
    p.id = post('op365_projects', {'op365_name': name, 'op365_contractvalue': value, 'op365_startdate': p.start.isoformat(),
                                   'op365_enddate': p.end.isoformat(), 'statuscode': 365000000,
                                   'op365_CustomerId@odata.bind': bind('accounts', p.customer),
                                   'op365_ProjectManagerId@odata.bind': bind('systemusers', me),
                                   'op365_description': f'{name}: {kind_label(kind)} for {CUSTOMERS[ci][0]}.', **OWNER})['op365_projectid']
    team = {role: r.choice(keys) for role, keys in ROLE_KEYS.items()}
    p.nodes, p.leaves = {}, []
    for i, (code, title, parent, s, e, hours, mat, roles) in enumerate(TEMPLATES[kind]):
        body = {'op365_ProjectId@odata.bind': bind('op365_projects', p.id), 'op365_code': code, 'op365_name': title, 'op365_sortorder': i}
        if parent:
            body['op365_ParentId@odata.bind'] = bind('op365_wbsnodes', p.nodes[parent]['id'])
        node = {'code': code, 'name': title}
        if s is not None:
            ns, ne = p.start + dt.timedelta(days=round(s * span)), p.start + dt.timedelta(days=round(e * span))
            h = max(8, round(hours * scale / 4) * 4)
            m = round(mat * scale, -2)
            avg = sum(COST[team[x]] for x in roles) / len(roles)
            body.update({'op365_startdate': ns.isoformat(), 'op365_enddate': ne.isoformat(), 'op365_budgethours': h,
                         'op365_budgetlabour': round(h * avg, -1), 'op365_budgetmaterials': m,
                         'op365_budgetother': round(m * 0.03, -1) if m else 0, 'op365_progresspct': 0})
            node.update(start=ns, end=ne, hours=h, materials=m, people=[team[x] for x in roles])
        node['id'] = post('op365_wbsnodes', body)['op365_wbsnodeid']
        if s is not None:
            for who in node['people']:
                post('op365_wbsallocations', {'op365_WbsNodeId@odata.bind': bind('op365_wbsnodes', node['id']),
                                              'op365_ResourceId@odata.bind': bind('op365_resources', RES[who]),
                                              'op365_hours': round(h / len(node['people']))})
            p.leaves.append(node)
        p.nodes[code] = node
    for a, b in LINKS[kind]:
        post('op365_wbsdependencies', {'op365_PredecessorId@odata.bind': bind('op365_wbsnodes', p.nodes[a]['id']),
                                       'op365_SuccessorId@odata.bind': bind('op365_wbsnodes', p.nodes[b]['id'])})
    if status != 'Offer':
        patch(f'op365_projects({p.id})', {'statuscode': 1})
        bound('op365_projects', p.id, 'op365_SaveBaseline', {'Name': 'Contract'})
        # the plan moved after the contract baseline on some projects
        if r.random() < 0.6:
            late = r.choice([l for l in p.leaves if l['end'] > TODAY] or p.leaves)
            shift = r.choice([5, 7, 10, 14])
            late['start'] += dt.timedelta(days=shift)
            late['end'] += dt.timedelta(days=shift)
            patch(f"op365_wbsnodes({late['id']})", {'op365_startdate': late['start'].isoformat(), 'op365_enddate': late['end'].isoformat()})
            if status == 'In Progress' and r.random() < 0.5:
                bound('op365_projects', p.id, 'op365_SaveBaseline', {'Name': 'Re-plan after change request'})
    else:
        bound('op365_projects', p.id, 'op365_SaveBaseline', {'Name': 'Offer'}, strict=False)
    # progress of the leaves at the reference date
    ref = p.end if status == 'Closed' else p.stop
    for leaf in p.leaves:
        if status == 'Closed':
            pct = 100
        elif status == 'Offer' or leaf['start'] > ref:
            pct = 0
        elif leaf['end'] <= ref and (status == 'Closed' or r.random() < 0.85):
            pct = 100
        else:
            elapsed = (ref - leaf['start']).days / max(1, (leaf['end'] - leaf['start']).days)
            pct = max(5, min(95, round((elapsed * 100 + r.randint(-15, 10)) / 5) * 5))
        leaf['pct'] = pct
        if pct:
            patch(f"op365_wbsnodes({leaf['id']})", {'op365_progresspct': pct})
    p.rnd = r
    return p


def kind_label(kind):
    return {'renovation': 'interior renovation and building services', 'pv': 'design and installation of a photovoltaic plant',
            'electrical': 'electrical distribution upgrade', 'hvac': 'heating, ventilation and air-conditioning works',
            'cabling': 'structured cabling and network', 'automation': 'industrial automation and control software',
            'fire': 'fire detection and suppression systems', 'ev': 'electric vehicle charging infrastructure',
            'led': 'LED lighting retrofit with controls', 'maintenance': 'yearly planned and reactive maintenance contract'}[kind]


projects = parallel(build_project, list(enumerate(PROJECTS)))
print('projects:', len(projects))

# ---------- time entries ----------
booked = {}  # (resource key, date) -> hours
plans = {}
for p in projects:
    if p.status == 'Offer':
        continue
    lo, hi = p.start, (p.end if p.status == 'Closed' else p.stop)
    rate = {}  # hours a day per person so that a finished node uses about its budget hours
    for leaf in p.leaves:
        workdays = sum(1 for i in range((leaf['end'] - leaf['start']).days + 1) if (leaf['start'] + dt.timedelta(days=i)).weekday() < 5)
        rate[leaf['id']] = min(8, max(1, leaf['hours'] / max(1, workdays) / len(leaf['people']) / 0.9))
    rows = []
    d = lo
    while d <= hi:
        for leaf in p.leaves:
            if not (leaf['start'] <= d <= leaf['end']):
                continue
            for who in leaf['people'] + (['pm'] if leaf is p.leaves[0] and d.weekday() == 0 else []):
                if d.weekday() not in WORKDAYS[who] or (who, d) in OFF or (None, d) in OFF or p.rnd.random() < 0.1:
                    continue
                want = 2 if who == 'pm' else max(1, round(rate[leaf['id']] * p.rnd.uniform(0.7, 1.3)))
                hours = min(want, 8 - booked.get((who, d), 0))
                if hours <= 0:
                    continue
                booked[(who, d)] = booked.get((who, d), 0) + hours
                rows.append((d, who, leaf, hours))
        d += dt.timedelta(days=1)
    plans[p.id] = rows


def log_time(p):
    out = []
    for d, who, leaf, hours in plans.get(p.id, []):
        body = {'op365_ProjectId@odata.bind': bind('op365_projects', p.id), 'op365_WbsNodeId@odata.bind': bind('op365_wbsnodes', leaf['id']),
                'op365_ResourceId@odata.bind': bind('op365_resources', RES[who]), 'op365_entrydate': d.isoformat(), 'op365_hours': hours}
        if p.rnd.random() < 0.3:
            body['op365_notes'] = p.rnd.choice(['Work as planned', 'Waiting for materials part of the day', 'Site meeting with the customer',
                                                'Snagging and clean-up', 'Testing and documentation', 'Travel to site included'])
        if who == 'pm' and user:
            body.update(OWNER)
        out.append((d, post('op365_timeentries', body)['op365_timeentryid']))
    return p, out


def chunks(seq, n=100):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


total = 0
for p, entries in parallel(log_time, [p for p in projects if p.status != 'Offer']):
    total += len(entries)
    if p.status == 'In Progress':
        older = [i for d, i in entries if d < MONDAY - dt.timedelta(days=7)]
        last_week = [i for d, i in entries if MONDAY - dt.timedelta(days=7) <= d < MONDAY]
    else:
        older, last_week = [i for _, i in entries], []
    for part in chunks(older):
        action('op365_SubmitTimeEntries', {'TimeEntryIds': part})
    rejected = p.rnd.sample(older, min(len(older), 2)) if p.status == 'In Progress' and p.rnd.random() < 0.5 else []
    approve = [i for i in older if i not in rejected]
    for part in chunks(approve):
        action('op365_DecideTimeEntries', {'TimeEntryIds': part, 'Approve': True}, strict=False)
    if rejected:
        action('op365_DecideTimeEntries', {'TimeEntryIds': rejected, 'Approve': False,
                                           'Note': 'Hours booked on the wrong task, please move them to the right WBS node.'}, strict=False)
    for part in chunks(last_week):
        action('op365_SubmitTimeEntries', {'TimeEntryIds': part})
print('time entries:', total)

# ---------- material usage ----------
def use_materials(p):
    if p.status == 'Offer':
        return 0
    r = p.rnd
    pool = [c for c, v in ITEM.items() if v[2] in CATEGORIES[p.kind]]
    ref = p.end if p.status == 'Closed' else p.stop
    count = 0
    for leaf in p.leaves:
        target = leaf['materials'] * leaf['pct'] / 100 * r.uniform(0.75, 1.05)
        parts = r.randint(1, 3)
        for code in r.sample(pool, min(parts, len(pool))):
            item, suppliers, _, uom, cost, _ = ITEM[code]
            qty = round(target / parts / cost) if uom == 'pcs' else round(target / parts / cost, -1)
            if qty < 1 or target <= 0:
                continue
            last = min(ref, leaf['end'])
            when = leaf['start'] + dt.timedelta(days=r.randint(0, max(0, (last - leaf['start']).days)))
            post('op365_materialusages', {'op365_ProjectId@odata.bind': bind('op365_projects', p.id),
                                          'op365_WbsNodeId@odata.bind': bind('op365_wbsnodes', leaf['id']),
                                          'op365_ItemId@odata.bind': bind('op365_items', item), 'op365_SupplierId@odata.bind': bind('accounts', suppliers[0]),
                                          'op365_quantity': qty, 'op365_usagedate': when.isoformat()})
            count += 1
    return count


print('material usage:', sum(parallel(use_materials, projects)))


# ---------- purchasing (In Progress projects only) ----------
def request(p, title, needed, lines, supplier=None):
    leaf = next((l for l in p.leaves if l['end'] >= TODAY), p.leaves[-1])
    body = {'op365_ProjectId@odata.bind': bind('op365_projects', p.id), 'op365_WbsNodeId@odata.bind': bind('op365_wbsnodes', leaf['id']),
            'op365_title': title, 'op365_neededby': D(needed), 'op365_justification': f'{title} for task {leaf["code"]} {leaf["name"]}.'}
    if supplier:
        body['op365_PreferredSupplierId@odata.bind'] = bind('accounts', supplier)
    if user:
        body['op365_RequesterId@odata.bind'] = bind('systemusers', me)
        body.update(OWNER)
    pr = post('op365_purchaserequests', body)['op365_purchaserequestid']
    out = []
    for code, qty in lines:
        out.append(post('op365_purchaserequestlines', {'op365_PurchaseRequestId@odata.bind': bind('op365_purchaserequests', pr),
                                                       'op365_ItemId@odata.bind': bind('op365_items', ITEM[code][0]),
                                                       'op365_quantity': qty})['op365_purchaserequestlineid'])
    return pr, out


def status_of(es, id_):
    return call('GET', f'{es}({id_})?$select=statuscode').json().get('statuscode')


def approve(pr):
    if bound('op365_purchaserequests', pr, 'op365_SubmitPurchaseRequest', strict=False) is None:
        return False
    for _ in range(2):  # above the threshold a second approval is needed
        if status_of('op365_purchaserequests', pr) != 365000000:
            break
        bound('op365_purchaserequests', pr, 'op365_DecidePurchaseRequest', {'Approve': True}, strict=False)
    return status_of('op365_purchaserequests', pr) == 365000001


def lines_for(p, n):
    pool = [c for c, v in ITEM.items() if v[2] in CATEGORIES[p.kind] and v[4] < 20000]
    picked = p.rnd.sample(pool, n)
    return [(c, p.rnd.choice([4, 8, 12, 20]) if ITEM[c][3] == 'pcs' else p.rnd.choice([100, 250, 500])) for c in picked]


def order_lines(po):
    return get(f'op365_purchaseorderlines?$select=op365_purchaseorderlineid,op365_quantity,op365_price,op365_name&$filter='
               f'_op365_purchaseorderid_value eq {po}&$orderby=op365_sortorder')


def receive(po, share, note_no, days_ago):
    rows = order_lines(po)
    lines = [f"{l['op365_purchaseorderlineid']}={max(1, round(l['op365_quantity'] * share))}" for l in rows]
    bound('op365_purchaseorders', po, 'op365_RegisterGoodsReceipt', {
        'Lines': lines, 'DeliveryNoteNumber': note_no, 'DeliveryNoteDate': D(-days_ago) + 'T00:00:00Z',
        'ReceiptDate': D(-days_ago) + 'T00:00:00Z'}, strict=False)
    return rows, share


def invoice(po, supplier, rows, share, number, decide=None):
    number_po = call('GET', f'op365_purchaseorders({po})?$select=op365_number').json().get('op365_number', '')
    inv = post('op365_supplierinvoices', {'op365_invoicenumber': number, 'op365_invoicedate': D(-2),
                                          'op365_SupplierId@odata.bind': bind('accounts', supplier),
                                          'op365_PurchaseOrderId@odata.bind': bind('op365_purchaseorders', po),
                                          'op365_orderrefs': f'PO {number_po}'})['op365_supplierinvoiceid']
    for n, l in enumerate(rows, 1):
        post('op365_supplierinvoicelines', {'op365_SupplierInvoiceId@odata.bind': bind('op365_supplierinvoices', inv), 'op365_linenumber': n,
                                            'op365_name': l['op365_name'], 'op365_quantity': max(1, round(l['op365_quantity'] * share)),
                                            'op365_unitprice': l['op365_price'], 'op365_vatrate': 22,
                                            'op365_OrderLineId@odata.bind': bind('op365_purchaseorderlines', l['op365_purchaseorderlineid'])})
    if decide is not None:
        body = {'Approve': decide} if decide else {'Approve': False, 'Note': 'Unit prices do not match the order, please issue a credit note.'}
        bound('op365_supplierinvoices', inv, 'op365_DecideSupplierInvoice', body, strict=False)


def via_rfq(p, title, scenario, k):
    lines = lines_for(p, 3)
    category = ITEM[lines[0][0]][2]
    suppliers = (SUPP_BY_CAT.get(category, []) + [ITEM[c][1][0] for c, _ in lines])
    suppliers = list(dict.fromkeys(suppliers))[:3]
    pr, req_lines = request(p, title, 20, lines, suppliers[0])
    if not approve(pr):
        return
    rfq = (bound('op365_purchaserequests', pr, 'op365_CreateRfq', {'Deadline': D(5) + 'T00:00:00Z', 'SupplierIds': suppliers}, strict=False) or {}).get('RfqId')
    if not rfq:
        return
    bound('op365_rfqs', rfq, 'op365_SendRfq', strict=False)
    inv = get(f'op365_rfqinvitations?$select=op365_rfqinvitationid,_op365_supplierid_value&$filter=_op365_rfqid_value eq {rfq}')
    answered = inv if scenario != 'waiting' else inv[:1]
    for n, i in enumerate(answered):
        patch(f"op365_rfqinvitations({i['op365_rfqinvitationid']})", {'op365_deliverydays': p.rnd.choice([5, 7, 10, 14, 21])}, strict=False)
        quotes = {q['_op365_requestlineid_value']: q['op365_rfqquoteid'] for q in get(
            f"op365_rfqquotes?$select=op365_rfqquoteid,_op365_requestlineid_value&$filter=_op365_invitationid_value eq {i['op365_rfqinvitationid']}")}
        for (code, _), line in zip(lines, req_lines):
            if line in quotes:
                patch(f'op365_rfqquotes({quotes[line]})', {'op365_price': round(ITEM[code][4] * p.rnd.uniform(0.85, 1.08), 2)}, strict=False)
    if scenario == 'waiting':
        return
    winner = answered[0]
    po = (bound('op365_rfqs', rfq, 'op365_AwardRfq', {'InvitationId': winner['op365_rfqinvitationid']}, strict=False) or {}).get('PurchaseOrderId')
    if not po:
        return
    supplier = winner['_op365_supplierid_value']
    patch(f'op365_purchaseorders({po})', {'op365_deliveryplace': f'Site: {p.name}', 'op365_expecteddelivery': D(p.rnd.randint(5, 25))}, strict=False)
    if scenario == 'awarded':
        return
    bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Sent'}, strict=False)
    bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Confirmed'}, strict=False)
    if scenario in ('partial', 'received'):
        share = 1 if scenario == 'received' else 0.5
        rows, share = receive(po, share, f'DN-{p.rnd.randint(10000, 99999)}', p.rnd.randint(1, 10))
        invoice(po, supplier, rows, share, f'INV/{TODAY.year}/{1000 + k}', decide=True if scenario == 'received' else None)


def direct(p, title, scenario, k):
    lines = lines_for(p, 2)
    supplier = ITEM[lines[0][0]][1][0]
    pr, _ = request(p, title, p.rnd.randint(10, 40), lines, supplier)
    if scenario == 'draft':
        return
    if scenario == 'rejected':
        bound('op365_purchaserequests', pr, 'op365_SubmitPurchaseRequest', strict=False)
        bound('op365_purchaserequests', pr, 'op365_DecidePurchaseRequest',
              {'Approve': False, 'Note': 'Already covered by stock on site, please reuse the leftover material.'}, strict=False)
        return
    if scenario == 'submitted':
        bound('op365_purchaserequests', pr, 'op365_SubmitPurchaseRequest', strict=False)
        return
    if scenario == 'cancelled':
        bound('op365_purchaserequests', pr, 'op365_CancelPurchaseRequest', strict=False)
        return
    if not approve(pr) or scenario == 'approved':
        return
    po = (bound('op365_purchaserequests', pr, 'op365_CreatePurchaseOrder', strict=False) or {}).get('PurchaseOrderId')
    if not po:
        return
    patch(f'op365_purchaseorders({po})', {'op365_expecteddelivery': D(p.rnd.randint(5, 30)), 'op365_deliveryplace': f'Site: {p.name}'}, strict=False)
    if scenario == 'po-draft':
        return
    bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Sent'}, strict=False)
    if scenario == 'po-received':
        bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Confirmed'}, strict=False)
        rows, share = receive(po, 1, f'DN-{p.rnd.randint(10000, 99999)}', p.rnd.randint(3, 15))
        invoice(po, supplier, rows, share, f'INV/{TODAY.year}/{2000 + k}', decide=False if k % 2 else None)


PURCHASES = [
    (0, via_rfq, 'Partition and ceiling materials', 'received'), (0, direct, 'Electrical consumables', 'po-sent'),
    (0, direct, 'Additional ceiling tiles', 'submitted'),
    (1, via_rfq, 'PV modules and inverters', 'partial'), (1, direct, 'Mounting rails', 'po-received'),
    (2, via_rfq, 'Switchboard and protection devices', 'awarded'), (2, direct, 'Spare breakers', 'rejected'),
    (3, via_rfq, 'Heat pumps and fan coils', 'received'), (3, direct, 'Ductwork accessories', 'po-draft'),
    (3, direct, 'Insulation materials', 'approved'),
    (4, via_rfq, 'Network cabling and racks', 'waiting'), (4, direct, 'Wi-Fi access points', 'draft'),
    (5, via_rfq, 'PLC hardware', 'partial'), (5, direct, 'Drives and I/O modules', 'po-sent'),
    (6, via_rfq, 'Detectors and sprinkler heads', 'awarded'), (6, direct, 'Fire alarm panel', 'cancelled'),
    (7, via_rfq, 'Wallboxes and fast chargers', 'waiting'), (7, direct, 'Cable for charger feeders', 'po-received'),
    (8, via_rfq, 'High bay fittings', 'received'), (8, direct, 'Lighting controls', 'submitted'),
    (9, direct, 'Maintenance spares Q4', 'po-received'), (10, direct, 'Plasterboard and studs', 'draft'),
    (11, direct, 'Battery storage modules', 'po-sent'),
]


def purchase(arg):
    k, (n, fn, title, scenario) = arg
    fn(projects[n], title, scenario, k)


parallel(purchase, list(enumerate(PURCHASES)))
print('purchase requests:', len(PURCHASES))

# ====================================================================================================================
# Timeline: notes, tasks, phone calls and appointments on every project
# ====================================================================================================================
CONTACTS = {}
for c in get('contacts?$select=contactid,fullname,_parentcustomerid_value'):
    CONTACTS.setdefault(c['_parentcustomerid_value'], []).append(c['fullname'])


def ts(d, hour=9):
    return f'{d.isoformat()}T{hour:02d}:00:00Z'


def timeline(p):
    r = p.rnd
    who = (CONTACTS.get(p.customer) or ['the customer'])[0]
    customer = p.customer_name
    ev = []  # (kind, date, subject, text, done)
    if p.status == 'Offer':
        first = TODAY - dt.timedelta(days=r.randint(20, 45))
        ev += [('phonecall', first, f'First contact with {who}', f'{who} asked for a quotation for {kind_label(p.kind)}.', True),
               ('appointment', first + dt.timedelta(days=6), 'Site survey', f'Survey at {customer} with {who}: measurements and photos taken.', True),
               ('note', first + dt.timedelta(days=7), 'Survey notes', 'Access only outside business hours on Saturdays. Power shutdowns must be agreed two weeks in advance.', True),
               ('task', first + dt.timedelta(days=14), 'Prepare technical and economic offer', 'Bill of quantities, labour estimate and schedule.', True),
               ('note', first + dt.timedelta(days=16), 'Offer sent', f'Offer of {p.value:,.0f} sent to {who}, valid 60 days.', True),
               ('phonecall', TODAY + dt.timedelta(days=r.randint(2, 6)), 'Follow-up call on the offer', f'Ask {who} for feedback and decision date.', False),
               ('appointment', TODAY + dt.timedelta(days=r.randint(8, 15)), 'Offer review meeting', 'Walk the customer through scope, exclusions and payment milestones.', False)]
    else:
        s, ref = p.start, (p.end if p.status == 'Closed' else p.stop)
        ev += [('note', s - dt.timedelta(days=10), 'Order received', f'Signed order from {customer}, contract value {p.value:,.0f}.', True),
               ('appointment', s, 'Kick-off meeting', f'Kick-off with {who}: scope, schedule, site rules and contacts confirmed.', True),
               ('note', s + dt.timedelta(days=1), 'Kick-off minutes', 'Weekly progress meeting on Tuesdays. Customer to provide site access badges and a storage area.', True),
               ('task', s + dt.timedelta(days=3), 'Submit risk assessment and method statement', 'RAMS to be approved by the customer HSE before work starts.', True)]
        d = s + dt.timedelta(days=14)
        n = 1
        while d < ref:
            ev.append(('appointment', d, f'Progress meeting #{n}', r.choice([
                'Works on schedule. Next steps agreed with the customer.',
                'Minor delays on deliveries, recovered with an extra crew on Saturday.',
                'Customer asked for two additional points; change request to be priced.',
                'Snag list reviewed, eight items open.']), True))
            d += dt.timedelta(days=r.choice([14, 21]))
            n += 1
        mid = s + (ref - s) / 2
        ev += [('phonecall', mid, f'Call with {who} about access', 'Agreed evening shifts for noisy works in the occupied area.', True),
               ('note', mid + dt.timedelta(days=2), r.choice(['Supplier delay', 'Change request', 'Site incident (no injury)']), r.choice([
                   'The supplier moved the delivery by one week; the plan was updated and the customer informed.',
                   'Customer requested extra works; quotation CR-01 sent for approval.',
                   'Near miss reported: unsecured ladder. Toolbox talk held with the crew.']), True)]
        if p.status == 'In Progress':
            ev += [('task', TODAY + dt.timedelta(days=r.randint(3, 10)), 'Send monthly progress report', 'Progress, costs to date and look-ahead for the next month.', False),
                   ('appointment', TODAY + dt.timedelta(days=r.randint(1, 8)), f'Progress meeting #{n}', 'Review progress and open points with the customer.', False),
                   ('task', TODAY + dt.timedelta(days=r.randint(5, 20)), 'Order long-lead materials', 'Check lead times with suppliers for the next phase.', False),
                   ('phonecall', TODAY + dt.timedelta(days=r.randint(1, 4)), f'Call {who} to confirm next site access', 'Confirm dates and working hours.', False)]
        elif p.status == 'Suspended':
            ev += [('note', p.stop, 'Project suspended', r.choice(['Customer put the works on hold pending budget approval for next year.',
                                                                   'Works stopped waiting for the landlord\'s building consent.'])
                    + ' Site made safe and demobilised.', True),
                   ('task', TODAY + dt.timedelta(days=r.randint(10, 30)), 'Check restart date with the customer', 'Ask for a written restart date.', False)]
        else:
            ev += [('appointment', p.end, 'Final inspection and handover', f'Handover to {who}; as-built drawings and certificates delivered.', True),
                   ('note', p.end + dt.timedelta(days=2), 'Final acceptance signed', 'Acceptance certificate signed without reservations. Warranty starts today.', True),
                   ('task', p.end + dt.timedelta(days=10), 'Archive project documentation', 'File drawings, certificates and the final cost report.', True)]
    regarding = bind('op365_projects', p.id)
    for kind, d, subject, text, done in ev:
        past = d <= TODAY
        created = ts(min(d, TODAY), 8)
        if kind == 'note':
            body = {'subject': subject, 'notetext': text, 'objectid_op365_project@odata.bind': regarding, 'overriddencreatedon': created}
            post('annotations', body)
            continue
        body = {'subject': subject, 'description': text, f'regardingobjectid_op365_project_{kind}@odata.bind': regarding, **OWNER}
        if past:
            body['overriddencreatedon'] = ts(d - dt.timedelta(days=3), 8)
        if kind == 'task':
            body.update({'scheduledend': ts(d, 17), 'prioritycode': r.choice([0, 1, 1, 2])})
        elif kind == 'phonecall':
            body.update({'scheduledend': ts(d, 11), 'phonenumber': phone(), 'directioncode': r.random() < 0.6})
        else:
            body.update({'scheduledstart': ts(d, 10), 'scheduledend': ts(d, 11), 'location': f'{customer} - site office'})
        a = post(f'{kind}s' if kind != 'phonecall' else 'phonecalls', body)
        if done and past:
            state = {'task': (1, 5), 'phonecall': (1, 2), 'appointment': (1, 3)}[kind]
            key = f'{kind}s' if kind != 'phonecall' else 'phonecalls'
            patch(f"{key}({a['activityid']})", {'statecode': state[0], 'statuscode': state[1], 'actualend': ts(d, 12)}, strict=False)
    return len(ev)


print('timeline records:', sum(parallel(timeline, projects)))

# ---------- final statuses ----------
for p in projects:
    if p.status == 'Suspended':
        patch(f'op365_projects({p.id})', {'statuscode': STATUS['Suspended']})
    elif p.status == 'Closed':
        patch(f'op365_projects({p.id})', {'statecode': 1, 'statuscode': 2})

for p in projects:
    v = call('GET', f'op365_projects({p.id})?$select=op365_code,op365_budgettotal,op365_actualcost,op365_committedcost,op365_actualhours,'
                    'op365_progresspct').json()
    print(f"{v.get('op365_code') or '':10} {p.status:11} {p.name[:44]:44} budget {v.get('op365_budgettotal') or 0:>10,.0f} "
          f"actual {v.get('op365_actualcost') or 0:>10,.0f} committed {v.get('op365_committedcost') or 0:>9,.0f} "
          f"hours {v.get('op365_actualhours') or 0:>6,.0f} progress {v.get('op365_progresspct') or 0:>3.0f}%")
