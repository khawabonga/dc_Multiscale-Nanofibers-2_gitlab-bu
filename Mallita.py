import numpy as np
from matplotlib import cm, pyplot as plt
from Aux import find_string_in_file, calcular_longitud_de_segmento

class Nodos(object):
    def __init__(self, n, r0, tipos):
        self.n = n
        self.r0 = np.array(r0, dtype=float)
        self.r = self.r0.copy()
        self.t = np.array(tipos, dtype=int)
        self.mf = self.t == 1
        self.mi = self.t == 2

class Fibras(object):
    def __init__(self, n, con, param):
        self.n = n
        self.con = np.array(con, dtype=int)
        self.param = np.array(param, dtype=float)
        self.longs0 = None
        self.drs0 = None
        self.__mr = np.zeros( (n,1), dtype=bool)
        self.__me = np.zeros( (n,1), dtype=bool)
        self.__fzas = np.zeros( (n,1), dtype=float )
        self.__fzasv = np.zeros( (n,2), dtype=float )

    def calcular_drs0_longs0_fzasr(self, r0):
        self.drs0 = r0[ self.con[:,1] ] - r0[ self.con[:,0] ]
        self.longs0 = np.sqrt( np.sum( self.drs0*self.drs0, axis=1, keepdims=True ) )
        self.fzas_r = np.zeros( (self.n,2), dtype=float )
        self.fzas_r = self.param[:,2,None] * (self.param[:,0,None] - 1.)

    def calcular_drs_longs_lams(self, r):
        drs = r[ self.con[:,1] ] - r[ self.con[:,0] ]
        longs = np.sqrt( np.sum( drs*drs, axis=1, keepdims=True ) )
        lams = longs / self.longs0
        return drs, longs, lams

    def calcular_fuerzas(self, r, longout=False):
        drs, longs, lams = self.calcular_drs_longs_lams(r)
        lams_r = self.param[:,0,None]
        ks1 = self.param[:,1,None]
        ks2 = self.param[:,2,None]
        self.__mr = np.greater(lams, lams_r) # mask rectas
        self.__me = np.logical_not(self.__mr) # mask enruladas
        i = self.__mr
        self.__fzas[i] = self.fzas_r[i] + ks1[i]*(lams[i]/lams_r[i] - 1.)
        i = self.__me
        self.__fzas[i] = ks2[i]*(lams[i] - 1.)
        self.__fzasv = self.__fzas/longs * drs
        if not longout:
            return self.__fzasv
        else:
            return drs, longs, lams, self.__fzas, self.__fzasv

    def calcular_fuerza(self, f, r_n0, r_n1, longout=False):
        dr = r_n1 - r_n0
        long = np.sqrt(np.sum(dr*dr))
        lam = long/self.longs0[f]
        lam_r, k1, k2 = self.param[f]
        fza_r = k2*(lam_r-1.)
        if lam <= lam_r:
            fza = k2*(lam-1.)
        else:
            fza = fza_r + k1*(lam/lam_r - 1.)
        fzav = fza/long * dr[:,None]
        if not longout:
            return fzav
        else:
            return dr, long, lam, fza, fzav

class Mallita(object):
    def __init__(self, nodos, fibras):
        self.nodos = nodos
        self.fibras = fibras
        self.fibras.calcular_drs0_longs0_fzasr(self.nodos.r0)
        self.__delta = 1.e-4
        self.__delta21 = 1. / (2.*self.__delta)
        self.__deltax = self.__delta * np.array( [1., 0.], dtype=float )
        self.__deltay = self.__delta * np.array( [0., 1.], dtype=float )

    @classmethod
    def desde_malla_completa(cls, mc, param_in):
        """
        toma una malla completa (mc)
        y construye una malla simplifiada
        mc es una instancia de malla completa
        param es un array con los parametros generales que se van a copiar para todas las fibras
         """
        # obtengo lo que necesito de la malla completa
        # recordar que en la malla completa los objetos suelen ser listas (no arrays de numpy)
        L = mc.L
        coors = mc.nods.r
        tipos = mc.nods.tipos
        segs = mc.segs.con
        fibs = mc.fibs.con
        # los voy a mapear a otras listas propias de la malla simplificada
        ms_nods_r = list() # coordenadas de la malla simplificada
        ms_nods_t = list() # tipos de los nodos de la malla simplificada
        ms_nods_n = list() # indices originales de los nodos
        ms_sfbs_c = list() # conectividad de subfibras de la malla simplificada
        ms_sfbs_lc = list() # largo de las subfibras siguiendo el contorno de los segmentos
        ms_sfbs_le = list() # largo de las subfibras de extremo a extremo
        # recorro cada fibra:
        for f in range(len(fibs)): # f es el indice de cada fibra en la malla completa
            # tengo una nueva subfibra
            new_sfb = [0, 0] # por ahora esta vacia
            # agrego el primer nodo
            s = fibs[f][0] # segmento 0 de la fibra f
            n0 = segs[s][0] # nodo 0 del segmento s
            ms_nods_r.append( coors[n0] )
            ms_nods_t.append( tipos[n0] ) # deberia ser un 1
            ms_nods_n.append( n0 )
            # lo agrego a la nueva subfibra como su primer nodo
            new_sfb[0] = ms_nods_n.index(n0)   # es el nodo recien agregado a la lista de nodos
            assert ms_nods_t[-1] == 1
            # recorro el resto de los nodos de la fibra para agregar los nodos intereccion
            loco = 0. # aca voy sumando el largo de los segmentos que componen la subfibra (loco = longitud de contorno)
            for js in range(len(fibs[f])): # js es el indice de cada segmento en la fibra f (numeracion local a la fibra)
                # voy viendo los nodos finales de cada segmento
                s = fibs[f][js] # s es el indice de cada segmento en la malla original (numeracion global)
                n0 = segs[s][0] # primer nodo del segmento
                n1 = segs[s][1] # nodo final del segmento
                r0 = coors[n0]
                r1 = coors[n1]
                dx = r1[0] - r0[0]
                dy = r1[1] - r0[1]
                loco += np.sqrt( dx*dx + dy*dy ) # largo del segmento (lo sumo al largo de la subfibra)
                if tipos[n1] in (1,2): # nodo interseccion (2) o nodo final (1)
                    # tengo que fijarme si el nodo no esta ya presente
                    # (ya que los nodos interseccion pertenecen a dos fibras)
                    if not n1 in ms_nods_n:
                        # el nodo no esta listado,
                        # tengo que agregarlo a la lista de nodos
                        ms_nods_r.append( coors[n1] )
                        ms_nods_t.append( tipos[n1] )
                        ms_nods_n.append( n1 )
                    # me fijo en la nueva numeracion cual es el indice del ultimo nodo de la subfibra
                    new_sfb[1] = ms_nods_n.index(n1)
                    # y agrega la conectividad de la subfibra a la lista
                    ms_sfbs_c.append( new_sfb )
                    # ademas agrego la longitud de contorno y la longitud de extremos a extremo
                    ms_sfbs_lc.append( loco )
                    n_e1 = new_sfb[1] # nodo extremo final de la subfibra
                    n_e0 = new_sfb[0] # nodo extremo inicial de la subfibra
                    dx = ms_nods_r[n_e1][0] - ms_nods_r[n_e0][0]
                    dy = ms_nods_r[n_e1][1] - ms_nods_r[n_e0][1]
                    lete = np.sqrt(dx*dx + dy*dy)
                    ms_sfbs_le.append( lete )
                    # si no llegue a un nodo frontera, debo empezar una nueva subfibra a partir del nodo interseccion
                    if tipos[n1] == 2:
                        loco = 0.
                        new_sfb = [0, 0]
                        new_sfb[0] = ms_nods_n.index(n1) # el primer nodo de la siguiente subfibra sera el ultimo nodo de la anterior
        # ---
        # ahora coloco las variables en mi objeto malla simplificada
        # nodos con coordenadas y tipos
        n_nods = len(ms_nods_r)
        nodos = Nodos(n_nods, ms_nods_r, ms_nods_t)
        # subfibras
        n_sfbs = len(ms_sfbs_c)
        locos = np.array( ms_sfbs_lc, dtype=float )
        letes = np.array( ms_sfbs_le, dtype=float )
        lams_r = locos / letes
        param = np.zeros( (n_sfbs,len(param_in)+1), dtype=float )
        param[:,0] = lams_r
        param[:,1:] = param_in
        fibras = Fibras(n_sfbs, ms_sfbs_c, param)
        # mallita
        m = Mallita(nodos, fibras)
        return m


    def calcular_fuerzas(self, longout=False):
        return self.fibras.calcular_fuerzas(self.nodos.r, longout)

    def deformar_frontera(self, F):
        self.nodos.r[self.nodos.mf] = np.matmul(self.nodos.r0[self.nodos.mf], np.transpose(F))

    def calcular_dr(self):
        dr = np.zeros( np.shape(self.nodos.r), dtype=float )
        r1 = self.nodos.r.copy() # posiciones actualizadas en iteraciones
        for i in range(10):
            A,b = self.calcular_A_b(r1)
            dr = np.linalg.solve(A,b)
            residuos = np.matmul(A,dr) - b
            error = np.max(np.abs( np.sqrt(np.sum(dr*dr, axis=1)) ))
            print i,":",error
            r1 += dr.reshape(-1,2)
            if error<1.e-10:
                break
        return r1

    def calcular_A_b(self, r1):
        """ calcula la matriz tangente A y el vector de cargas b
        alrededor de las posiciones dadas por r1
        que es tipicamente el array de posiciones en la iteracion previa """
        # seteo matrices
        nG = self.nodos.n*2
        matG = np.zeros( (nG,nG), dtype=float  )
        vecG = np.zeros( (nG,1), dtype=float )
        nL = 2 # tengo que armar la matriz tangente respecto de un solo nodo (hay doble simetria)
        matL = np.zeros( (nL,nL), dtype=float )
        vecL = np.zeros( (nL,1), dtype=float )
        for f, (n0,n1) in enumerate(self.fibras.con):
            if f==2:
                pass
            r_n0 = r1[n0]
            r_n1 = r1[n1]
            r_n0_px = r1[n0] + self.__deltax
            r_n0_mx = r1[n0] - self.__deltax
            r_n0_py = r1[n0] + self.__deltay
            r_n0_my = r1[n0] - self.__deltay
            F_c = self.fibras.calcular_fuerza(f, r_n0, r_n1)
            F_mx = self.fibras.calcular_fuerza(f, r_n0_mx, r_n1)
            F_px = self.fibras.calcular_fuerza(f, r_n0_px, r_n1)
            F_my = self.fibras.calcular_fuerza(f, r_n0_my, r_n1)
            F_py = self.fibras.calcular_fuerza(f, r_n0_py, r_n1)
            dFdx = (F_px - F_mx) * self.__delta21
            dFdy = (F_py - F_my) * self.__delta21
            matL[:,0] = dFdx[:,0]
            matL[:,1] = dFdy[:,0]
            vecL = - F_c
            # ahora a ensamblar
            # primero el vector de cargas
            row = n0*2
            col = n1*2
            vecG[row:row+2] += vecL
            vecG[col:col+2] += -vecL
            # luego matriz local va a 4 submatrices de la global
            # primero en el nodo 0
            row = n0*2
            col = n0*2
            matG[row:row+2,col:col+2] += matL
            # luego lo mismo en el nodo 1
            row = n1*2
            col = n1*2
            matG[row:row+2,col:col+2] += matL
            # luego las cruzadas
            row = n0*2
            col = n1*2
            matG[row:row+2,col:col+2] += - matL
            row = n1*2
            col = n0*2
            matG[row:row+2,col:col+2] += - matL
        # ahora las condiciones de dirichlet
        for n in range(self.nodos.n):
            if self.nodos.t[n] == 1:
                ix = 2*n
                iy = 2*n+1
                matG[ix,:] = 0.
                matG[ix,ix] = 1.
                vecG[ix] = 0.
                matG[iy,:] = 0.
                matG[iy,iy] = 1.
                vecG[iy] = 0.
        # fin
        return matG, vecG

    def pre_graficar_0(self, fig, ax, lamr_min=None, lamr_max=None):
        mi_cm = plt.cm.rainbow
        lamsr = self.fibras.param[:,0]
        if lamr_min is None:
            lamr_min = np.min(lamsr)
        if lamr_max is None:
            lamr_max = np.max(lamsr)
        sm = plt.cm.ScalarMappable(cmap=mi_cm, norm=plt.Normalize(vmin=lamr_min, vmax=lamr_max))
        for f, (n0,n1) in enumerate(self.fibras.con):
            # linea inicial
            x0,y0 = self.nodos.r0[n0]
            x1,y1 = self.nodos.r0[n1]
            c = sm.to_rgba(lamsr[f])
            ax.plot([x0,x1], [y0,y1], ls="--", c=c)
            # # linea final
            # x0,y0 = self.nodos.r[n0]
            # x1,y1 = self.nodos.r[n1]
            # ax.plot([x0,x1], [y0,y1], ls="-", c="k")
        sm._A = []
        fig.colorbar(sm)

    def pre_graficar(self, fig, ax, lam_min=None, lam_max=None, initial=True):
        mi_cm = plt.cm.rainbow
        drs, longs, lams = self.fibras.calcular_drs_longs_lams(self.nodos.r)
        if lam_min is None:
            lam_min = np.min(lams)
        if lam_max is None:
            lam_max = np.max(lams)
        sm = plt.cm.ScalarMappable(cmap=mi_cm, norm=plt.Normalize(vmin=lam_min, vmax=lam_max))
        for f, (n0,n1) in enumerate(self.fibras.con):
            # linea inicial
            x0,y0 = self.nodos.r0[n0]
            x1,y1 = self.nodos.r0[n1]
            ax.plot([x0,x1], [y0,y1], ls="--", c="gray")
            # linea final
            x0,y0 = self.nodos.r[n0]
            x1,y1 = self.nodos.r[n1]
            c = sm.to_rgba(lams[f])
            ax.plot([x0,x1], [y0,y1], ls="-", c="k")
        sm._A = []
        fig.colorbar(sm)

    # def graficar(self):
    #     fig, ax = plt.subplots()
    #     self.pregraficar(fig, ax)
    #     plt.show()

# nnodos = 6
# r0 = np.array(
#     [
#         [0., 0.],
#         [1., 0.],
#         [1., 1.],
#         [0., 1.],
#         [.2, .5],
#         [.8, .5]
#     ],
#     dtype=float
# )
# # tipos (1=frontera, 2=interseccion)
# tipos = np.array(
#     [1, 1, 1, 1, 2, 2],
#     dtype=int
# )

# nodos = Nodos(nnodos, r0, tipos)

# nfibras = 5
# fibras_con = np.array(
#     [
#         [0,4],
#         [1,5],
#         [2,5],
#         [3,4],
#         [4,5]
#     ],
#     dtype=int
# )
# # parametros constitutivos
# param = np.array(
#     [
#         [1.0, 10., .01],
#         [1.0, 10., .01],
#         [1.0, 10., .01],
#         [1.0, 10., .01],
#         [1.0, 10., .01]
#     ],
#     dtype=float
# )

# fibras = Fibras(nfibras, fibras_con, param)

# m = Mallita(nodos, fibras)

# Fmacro = np.array(
#     [
#         [1.1, 0.0],
#         [0.1, 1.0]
#     ],
#     dtype=float
# )


# # # m.nodos.r[1,:] = [1.1, 0.]
# # # m.nodos.r[2,:] = [1.1, 1.]
# m.deformar_frontera(Fmacro)

# print m.nodos.r0
# print
# print m.nodos.r
# print

# r = m.calcular_dr()

# print r

# m.nodos.r = r
# m.graficar()

# F = m.calcular_fuerzas()
# print "F"
# print F
# print "---"

# A, b = m.calcular_A_b()

# print "A // b"
# msg = ""
# for n in range(m.nodos.n):
#     for i in range(2):
#         for o in range(m.nodos.n):
#             msg += "{:12.2e}{:12.2e}".format(A[2*n+i,2*o+0],A[2*n+i,2*o+1])
#         msg += "  //  "
#         msg += "{:12.2e}".format(b[2*n+i,0])
#         msg += "\n"
# print msg
# print "---"



# dr = np.linalg.solve(A,b)
# print "dr"
# print dr
# print "---"