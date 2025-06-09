from .registry import register

from qiskit_ibm_runtime.fake_provider import (
    FakeAlgiers,
    FakeAlmadenV2,
    FakeArmonkV2,
    FakeAthensV2,
    FakeAuckland,
    FakeBelemV2,
    FakeBoeblingenV2,
    FakeBogotaV2,
    FakeBrisbane,
    FakeBrooklynV2,
    FakeBurlingtonV2,
    FakeCairoV2,
    FakeCambridgeV2,
    FakeCasablancaV2,
    FakeCusco,
    FakeEssexV2,
    FakeFez,
    FakeFractionalBackend,
    FakeGeneva,
    FakeGuadalupeV2,
    FakeHanoiV2,
    FakeJakartaV2,
    FakeJohannesburgV2,
    FakeKawasaki,
    FakeKolkataV2,
    FakeKyiv,
    FakeKyoto,
    FakeLagosV2,
    FakeLimaV2,
    FakeLondonV2,
    FakeManhattanV2,
    FakeManilaV2,
    FakeMelbourneV2,
    FakeMarrakesh,
    FakeMontrealV2,
    FakeMumbaiV2,
    FakeNairobiV2,
    FakeOsaka,
    FakeOslo,
    FakeOurenseV2,
    FakeParisV2,
    FakePeekskill,
    FakePerth,
    FakePrague,
    FakePoughkeepsieV2,
    FakeQuebec,
    FakeQuitoV2,
    FakeRochesterV2,
    FakeRomeV2,
    FakeSantiagoV2,
    FakeSherbrooke,
    FakeSingaporeV2,
    FakeSydneyV2,
    FakeTorino,
    FakeTorontoV2,
    FakeValenciaV2,
    FakeVigoV2,
    FakeWashingtonV2,
    FakeYorktownV2,
)

register.add_target_device("ibm_fake_algiers", FakeAlgiers().target)
register.add_target_device("ibm_fake_almaden", FakeAlmadenV2().target)
register.add_target_device("ibm_fake_armonk", FakeArmonkV2().target)
register.add_target_device("ibm_fake_athens", FakeAthensV2().target)
register.add_target_device("ibm_fake_auckland", FakeAuckland().target)
register.add_target_device("ibm_fake_belem", FakeBelemV2().target)
register.add_target_device("ibm_fake_boeblingen", FakeBoeblingenV2().target)
register.add_target_device("ibm_fake_bogota", FakeBogotaV2().target)
register.add_target_device("ibm_fake_brisbane", FakeBrisbane().target)
register.add_target_device("ibm_fake_brooklyn", FakeBrooklynV2().target)
register.add_target_device("ibm_fake_burlington", FakeBurlingtonV2().target)
register.add_target_device("ibm_fake_cairo", FakeCairoV2().target)
register.add_target_device("ibm_fake_cambridge", FakeCambridgeV2().target)
register.add_target_device("ibm_fake_casablanca", FakeCasablancaV2().target)
register.add_target_device("ibm_fake_cusco", FakeCusco().target)
register.add_target_device("ibm_fake_essex", FakeEssexV2().target)
register.add_target_device("ibm_fake_fez", FakeFez().target)
register.add_target_device("ibm_fake_fractional", FakeFractionalBackend().target)
register.add_target_device("ibm_fake_geneva", FakeGeneva().target)
register.add_target_device("ibm_fake_guadalupe", FakeGuadalupeV2().target)
register.add_target_device("ibm_fake_hanoi", FakeHanoiV2().target)
register.add_target_device("ibm_fake_jakarta", FakeJakartaV2().target)
register.add_target_device("ibm_fake_johannesburg", FakeJohannesburgV2().target)
register.add_target_device("ibm_fake_kawasaki", FakeKawasaki().target)
register.add_target_device("ibm_fake_kolkata", FakeKolkataV2().target)
register.add_target_device("ibm_fake_kyiv", FakeKyiv().target)
register.add_target_device("ibm_fake_kyoto", FakeKyoto().target)
register.add_target_device("ibm_fake_lagos", FakeLagosV2().target)
register.add_target_device("ibm_fake_lima", FakeLimaV2().target)
register.add_target_device("ibm_fake_london", FakeLondonV2().target)
register.add_target_device("ibm_fake_manhattan", FakeManhattanV2().target)
register.add_target_device("ibm_fake_manila", FakeManilaV2().target)
register.add_target_device("ibm_fake_melbourne", FakeMelbourneV2().target)
register.add_target_device("ibm_fake_marrakesh", FakeMarrakesh().target)
register.add_target_device("ibm_fake_montreal", FakeMontrealV2().target)
register.add_target_device("ibm_fake_mumbai", FakeMumbaiV2().target)
register.add_target_device("ibm_fake_nairobi", FakeNairobiV2().target)
register.add_target_device("ibm_fake_osaka", FakeOsaka().target)
register.add_target_device("ibm_fake_oslo", FakeOslo().target)
register.add_target_device("ibm_fake_ourense", FakeOurenseV2().target)
register.add_target_device("ibm_fake_paris", FakeParisV2().target)
register.add_target_device("ibm_fake_peekskill", FakePeekskill().target)
register.add_target_device("ibm_fake_perth", FakePerth().target)
register.add_target_device("ibm_fake_prague", FakePrague().target)
register.add_target_device("ibm_fake_poughkeepsie", FakePoughkeepsieV2().target)
register.add_target_device("ibm_fake_quebec", FakeQuebec().target)
register.add_target_device("ibm_fake_quito", FakeQuitoV2().target)
register.add_target_device("ibm_fake_rochester", FakeRochesterV2().target)
register.add_target_device("ibm_fake_rome", FakeRomeV2().target)
register.add_target_device("ibm_fake_santiago", FakeSantiagoV2().target)
register.add_target_device("ibm_fake_sherbrooke", FakeSherbrooke().target)
register.add_target_device("ibm_fake_singapore", FakeSingaporeV2().target)
register.add_target_device("ibm_fake_sydney", FakeSydneyV2().target)
register.add_target_device("ibm_fake_torino", FakeTorino().target)
register.add_target_device("ibm_fake_toronto", FakeTorontoV2().target)
register.add_target_device("ibm_fake_valencia", FakeValenciaV2().target)
register.add_target_device("ibm_fake_vigo", FakeVigoV2().target)
register.add_target_device("ibm_fake_washington", FakeWashingtonV2().target)
register.add_target_device("ibm_fake_yorktown", FakeYorktownV2().target)
