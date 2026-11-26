import copy,unittest
from shapely.geometry import Polygon,GeometryCollection,mapping
from .spatial import profile,distances,state_distances

def fixture():
    p=Polygon([(0,0),(4,0),(4,4),(0,4)])
    l={'rooms':[{'id':'a','polygon':list(p.exterior.coords),'role':'fake_hub'}],'portals':[],'obstacles':[],
       'floor':mapping(p),'base_obstacles':mapping(GeometryCollection())}
    rows=[{'x_m':x,'z_m':z,'integration':i+1,'connectivity':i,'metric_m':2+i} for i,(x,z) in enumerate([(1,1),(1,2),(2,1),(2,2)])]
    return l,rows

class SpatialTest(unittest.TestCase):
    def test_same_profile_zero_distance(self):
        l,r=fixture();p=profile(r,l);self.assertEqual(distances(p,p),{'global_distance':0.,'regional_distance':0.})
    def test_label_change_cannot_improve_score(self):
        l,r=fixture();a=profile(r,l);l['rooms'][0].update(id='renamed',role='official_core');self.assertEqual(a,profile(r,l))
    def test_uniform_scale_metric_normalization(self):
        l,r=fixture();a=profile(r,l)
        from shapely.affinity import scale
        p=scale(Polygon(l['rooms'][0]['polygon']),10,10,origin=(0,0));l['floor']=mapping(p);l['rooms'][0]['polygon']=list(p.exterior.coords)
        for v in r:v['x_m']*=10;v['z_m']*=10;v['metric_m']*=10
        self.assertEqual(distances(profile(r,l),a),{'global_distance':0.,'regional_distance':0.})
    def test_candidate_spread_does_not_reset_scale(self):
        l,r=fixture();a=profile(r,l);b=copy.deepcopy(a)
        for k in b['global']:b['global'][k]=[v*10 for v in b['global'][k]]
        self.assertGreater(distances(b,a)['global_distance'],1)
    def test_missing_role_penalized(self):
        l,r=fixture();a=profile(r,l);b=copy.deepcopy(a);b['roles']={}
        self.assertEqual(distances(b,a)['regional_distance'],1)
    def test_state_is_not_silently_omitted(self):
        l,r=fixture();p=profile(r,l)
        with self.assertRaises(ValueError):state_distances({'initial':p},{'initial':p})

if __name__=='__main__':unittest.main()
