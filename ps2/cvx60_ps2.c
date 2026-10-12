/* CVX60 for Resident Evil CODE:Veronica X, PS2 USA (SLUS-20184), as a PCSX2 pnach.
 * Same scheme as the GameCube mod (mod/cvx60.c): per 30Hz tick, frame A is the tick's own draw with the
 * camera, bones and effects at the midpoint of last tick and this one, presented one vblank early;
 * frame B is an exact redraw presented on the next vblank. Game logic, input and audio are untouched.
 * Addresses and offsets come from the recvx-decomp symbol map / types.h (SLUS_201.84 sha1 f6c26ed6...).
 * Built with ee-gcc 2.9 (C89: declarations at block start). All mutable state is in .bss: pnach lines
 * rewrite the code/rodata area every frame. */
typedef unsigned int u32;
typedef unsigned char u8;
typedef float f32;
/* region: USA SLUS-20184 (default), PAL SLES-50306 (-DCVX_PAL; needs a 60Hz Mode patch) or JP SLPM-65022 (-DCVX_JPN). Same code
 * and SYS_WORK layout; only addresses differ (ps2eu_/ps2jp_ map.json and data.json). */
#if defined(CVX_PAL)
#define RG(usa, pal, jpn) (pal)
#elif defined(CVX_JPN)
#define RG(usa, pal, jpn) (jpn)
#else
#define RG(usa, pal, jpn) (usa)
#endif
#define FN(a, r, args...) ((r (*)(args))(a))

/* ---- game ---- */
#define SYSP (*(u8 **)RG(0x00303C90, 0x0030C090, 0x00302C90))
#define PLP (*(u8 **)RG(0x00303CA0, 0x0030C0A0, 0x00302CA0))
#define SYS32(o) (*(volatile u32 *)(SYSP + (o)))
#define SYSF(o) (*(volatile f32 *)(SYSP + (o)))
#define CAM_BASE RG(0x00432860, 0x00449090, 0x00430360)
#define CAM_FLG (*(volatile u32 *)CAM_BASE)
#define CAM_MTX (*(f32 **)(CAM_BASE + 0x9C))
#define CAM_PERS (*(volatile int *)(CAM_BASE + 0x84))
#define CAM_NCUT (*(volatile int *)(CAM_BASE + 0x8C))
#define PL_SLEEP (*(volatile u8 *)RG(0x0047D258, 0x00493A88, 0x0047AD40))
#define Ps2_vcount (*(volatile int *)RG(0x0112C798, 0x01144398, 0x0113A298))
#define Ps2_dbuff (*(volatile int *)RG(0x0112C790, 0x01144390, 0x0113A290))
#define VsyncFunc (*(void (**)(void))RG(0x0112C7A0, 0x011443A0, 0x0113A2A0))
#define EorFunc (*(void (**)(void))RG(0x0112C7A8, 0x011443A8, 0x0113A2A8))
#define Db ((void *)RG(0x0112C7B0, 0x011443B0, 0x0113A2B0))
#define T0_COUNT (*(volatile u32 *)0x10000000)

#define pdGetPeripheral FN(RG(0x002D9CF0, 0x002E1220, 0x002D8DA0), void *, int)
#define PS2_jikken FN(RG(0x002CB5C0, 0x002D2AF0, 0x002CA660), void, void)
#define SyncPath FN(RG(0x002E7AF0, 0x002EF0C0, 0x002E6B10), void, void)
#define Ps2DrawOTag FN(RG(0x002CCD10, 0x002D4240, 0x002CBDB0), void, void)
#define Ps2ClearOT FN(RG(0x002CC850, 0x002D3D80, 0x002CB8F0), void, void)
#define PS2_swap FN(RG(0x002CB5F0, 0x002D2B20, 0x002CA690), void, void)
#define sceGsSwapDBuffDc FN(0x00101E28, int, void *, int)
#define bhAllDrawModel FN(RG(0x001380D0, 0x001386B0, 0x00137920), void, void)
#define bhSetLight FN(RG(0x00282930, 0x00287520, 0x00281B50), void, void)
#define bhControlLight FN(RG(0x00281270, 0x00285E60, 0x00280490), void, void)
#define njSetPerspective FN(RG(0x002E2A80, 0x002EA030, 0x002E1AA0), void, int)
#define bhDrawCinesco FN(RG(0x0026C590, 0x0026CBE0, 0x0026BC60), void, void)
#define bhDrawScreenFade FN(RG(0x0026C070, 0x0026C6C0, 0x0026B740), void, void)
#define bhDrawScope FN(RG(0x0026C710, 0x0026CD60, 0x0026BDE0), void, void)
#define bhDispTime FN(RG(0x002B8C80, 0x002BE920, 0x002B8180), void, f32 *, int, int, int, f32)
#define bhCkFlg FN(RG(0x00280EA0, 0x00285A90, 0x002800C0), int, void *, int)

/* SYS_WORK (PS2 offsets, types.h) */
#define S_SS_FLG 0x40
#define S_TK_FLG 0x54
#define S_TS_FLG 0x58
#define S_GM_FLG 0x5C
#define S_ST_FLG 0x60
#define S_CB_FLG 0x64
#define S_GM_MODE 0x8C
#define S_LOOP_CT 0x1B05C
#define S_EVT_TIM 0x1B164
#define S_FADE_AN 0x2A5C4
#define S_SSV_MD0 0x2A5F4
#define S_SSV_AN 0x2A608
#define S_CINE_AN 0x2A62C

#define MAXENT 96
#define POOLMTX 640
#define PLAYER_RESERVE 40
#define EF_SAVE_MAX 512

typedef struct {
    u8 *key;   /* O_WORK array of the model */
    int n;     /* bone count */
    f32 *cur;  /* n * 12 floats (GX 3x4 layout) in this tick's pool */
    f32 *prev; /* n * 12 floats in last tick's pool, or 0 */
} Ent;

static struct {
    u32 tick;
    int interp, phase, cam_ok, in_a, cut_prev, nomodel;
    f32 cam[2][12];     /* view matrix at draw time, GX 3x4 layout */
    f32 camraw[2][16];  /* the same, as stored by the game (4x4) */
    u32 cam_tick[2];
    int cam_cut[2];
    int pers[2];
    u32 gm_draw;
    f32 campos[3]; int camang[3];   /* cam.px/py/pz, ax/ay/az at draw time */
    Ent ent[2][MAXENT];
    int nent[2];
    int used[2];
    f32 pool[2][POOLMTX * 12];
    f32 scratch[64 * 16];
    f32 cam_dt, cam_dr;
} S;

/* diagnostics read from outside (pmem + symbols) */
static struct {
    u32 off;        /* non-zero: vanilla 30fps path */
    u32 frames, extra, late, vanilla, camok, camcut, camfar, poserej;
    u32 why_last, why_or;
    u32 fake_on;    /* lab: buttons held (OR'ed into sys->pad_on) */
    u32 fake_ps;    /* lab: buttons pressed once (OR'ed into sys->pad_ps) */
    u32 bskip;      /* extra frames skipped because a cut was applied after the draw */
    u32 ptcl;       /* particle clouds interpolated (frame A) */
    u32 blood;      /* blood sprays interpolated (frame A) */
    u32 snow;       /* snow boxes interpolated (frame A) */
    u32 door;       /* door-transition ticks shown at 60 */
    u32 door_bail[4]; /* door ticks shown vanilla: off/late, slot mismatch, status, - */
} cvx_D;

static u32 cvx_build_seen;
extern u32 __bss_start[], __bss_end[];
static void state_check(void)
{
    u32 *p;
    if (cvx_build_seen == CVX_BUILD_ID) return;
    for (p = __bss_start; p < __bss_end; p++) *p = 0;
    cvx_build_seen = CVX_BUILD_ID;
}

/* ---- math (GX 3x4 layout: rows i, translation in [i*4+3]) ---- */
static f32 fabsf_(f32 x) { return x < 0 ? -x : x; }
static f32 rsqrt(f32 x)
{
    f32 r;
    __asm__("sqrt.s %0, %1" : "=f"(r) : "f"(x));
    return 1.0f / r;
}

/* PS2 Ninja 4x4 (row vectors, translation [12..14]) <-> GX 3x4 */
static void to_gx(f32 *g, const f32 *m)
{
    int i, j;
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) g[i * 4 + j] = m[j * 4 + i];
        g[i * 4 + 3] = m[12 + i];
    }
}
static void from_gx(f32 *m, const f32 *g)
{
    int i, j;
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) m[j * 4 + i] = g[i * 4 + j];
        m[12 + i] = g[i * 4 + 3];
    }
    /* m[3], m[7], m[11], m[15] are left as they are (0, 0, 0, 1 for affine matrices) */
}

static void copy16(f32 *d, const f32 *s) { int i; for (i = 0; i < 16; i++) d[i] = s[i]; }

static void mtx_mid(f32 *d, const f32 *a, const f32 *b)
{
    int i, c;
    for (i = 0; i < 12; i++) d[i] = 0.5f * (a[i] + b[i]);
    for (c = 0; c < 3; c++) {
        f32 la = a[c] * a[c] + a[4 + c] * a[4 + c] + a[8 + c] * a[8 + c];
        f32 lb = b[c] * b[c] + b[4 + c] * b[4 + c] + b[8 + c] * b[8 + c];
        f32 ld = d[c] * d[c] + d[4 + c] * d[4 + c] + d[8 + c] * d[8 + c];
        f32 want, k;
        if (la < 1e-12f || lb < 1e-12f || ld < 1e-12f) continue;
        want = 0.5f * (la * rsqrt(la) + lb * rsqrt(lb));
        k = want * rsqrt(ld);
        d[c] *= k; d[4 + c] *= k; d[8 + c] *= k;
    }
}

static void norm3(f32 *v)
{
    f32 l = v[0] * v[0] + v[1] * v[1] + v[2] * v[2], k;
    if (l < 1e-20f) return;
    k = rsqrt(l);
    v[0] *= k; v[1] *= k; v[2] *= k;
}

/* halfway camera: blend eye position and orientation separately, then rebuild (see mod/cvx60.c) */
static void cam_mid(f32 *d, const f32 *a, const f32 *b)
{
    f32 pa[3], pb[3], p[3], r[3][3], c[3], dt;
    int i, j;
    for (j = 0; j < 3; j++) {
        pa[j] = -(a[j] * a[3] + a[4 + j] * a[7] + a[8 + j] * a[11]);
        pb[j] = -(b[j] * b[3] + b[4 + j] * b[7] + b[8 + j] * b[11]);
        p[j] = 0.5f * (pa[j] + pb[j]);
    }
    for (i = 0; i < 3; i++)
        for (j = 0; j < 3; j++) r[i][j] = 0.5f * (a[i * 4 + j] + b[i * 4 + j]);
    norm3(r[0]);
    dt = r[1][0] * r[0][0] + r[1][1] * r[0][1] + r[1][2] * r[0][2];
    for (j = 0; j < 3; j++) r[1][j] -= dt * r[0][j];
    norm3(r[1]);
    c[0] = r[0][1] * r[1][2] - r[0][2] * r[1][1];
    c[1] = r[0][2] * r[1][0] - r[0][0] * r[1][2];
    c[2] = r[0][0] * r[1][1] - r[0][1] * r[1][0];
    if (c[0] * r[2][0] + c[1] * r[2][1] + c[2] * r[2][2] < 0.0f) { c[0] = -c[0]; c[1] = -c[1]; c[2] = -c[2]; }
    for (j = 0; j < 3; j++) r[2][j] = c[j];
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) d[i * 4 + j] = r[i][j];
        d[i * 4 + 3] = -(r[i][0] * p[0] + r[i][1] * p[1] + r[i][2] * p[2]);
    }
}

/* The PS2 view matrix is not rigid: bhControlCamera starts from cmat, whose camera-space axes carry the
 * aspect scale (x 0.75, more with a widescreen patch). Divide each camera-space row (rotation and
 * translation) by its length, blend the rigid transforms, then put the averaged scale back. */
static void cam_mid_s(f32 *d, const f32 *a, const f32 *b)
{
    f32 na[12], nb[12], sa[3], sb[3], s;
    int i, j;
    for (i = 0; i < 3; i++) {
        sa[i] = a[i * 4] * a[i * 4] + a[i * 4 + 1] * a[i * 4 + 1] + a[i * 4 + 2] * a[i * 4 + 2];
        sb[i] = b[i * 4] * b[i * 4] + b[i * 4 + 1] * b[i * 4 + 1] + b[i * 4 + 2] * b[i * 4 + 2];
        sa[i] = sa[i] > 1e-12f ? sa[i] * rsqrt(sa[i]) : 1.0f;
        sb[i] = sb[i] > 1e-12f ? sb[i] * rsqrt(sb[i]) : 1.0f;
        for (j = 0; j < 4; j++) { na[i * 4 + j] = a[i * 4 + j] / sa[i]; nb[i * 4 + j] = b[i * 4 + j] / sb[i]; }
    }
    cam_mid(d, na, nb);
    for (i = 0; i < 3; i++) {
        s = 0.5f * (sa[i] + sb[i]);
        for (j = 0; j < 4; j++) d[i * 4 + j] *= s;
    }
}

static int mtx_close(const f32 *a, const f32 *b, f32 max_move)
{
    f32 dx = a[3] - b[3], dy = a[7] - b[7], dz = a[11] - b[11];
    int i;
    if (dx * dx + dy * dy + dz * dz > max_move * max_move) return 0;
    for (i = 0; i < 12; i++) {
        if (i == 3 || i == 7 || i == 11) continue;
        if (fabsf_(a[i] - b[i]) > 0.9f) return 0;
    }
    return 1;
}

static int pose_close(const f32 *a, const f32 *b, int n, f32 max_move)
{
    int k, c;
    if (!mtx_close(a, b, max_move)) return 0;
    for (k = 0; k < n * 12; k++) {
        c = k % 12;
        if (c == 3 || c == 7 || c == 11) continue;
        if (fabsf_(a[k] - b[k]) > 0.6f) return 0;
    }
    return 1;
}

/* ---- when is it safe to interpolate? ---- */
#define TASKS_OK ((1u << 6) | (1u << 7) | (1u << 8) | (1u << 20) | (1u << 21) | (1u << 22))

static int in_event(void)
{
    return SYSP && ((SYS32(S_ST_FLG) & 0x1000001u) || (CAM_FLG & 0x2u));
}

static u32 interp_block(void)
{
    u32 why = 0, act;
    if (!SYSP) return 1u << 0;
    act = SYS32(S_TK_FLG) & ~SYS32(S_TS_FLG);
    if (!(act & (1u << 7))) why |= 1u << 1;                        /* gameplay task off */
    if (act & ~TASKS_OK) why |= 1u << 2;                           /* other task running */
    if (SYS32(S_SS_FLG) & 0x80000000u) why |= 1u << 3;             /* pause */
    if (SYS32(S_ST_FLG) & 0x100u) why |= 1u << 5;                  /* mirror */
    if (SYS32(S_ST_FLG) & 0x40000000u) why |= 1u << 6;            /* thermometer (animates per call) */
    if (SYS32(S_ST_FLG) & 0x8u) why |= 1u << 7;                    /* menu */
    if (SYS32(S_GM_FLG) & 0x100u) why |= 1u << 8;                  /* full-screen render to texture */
    if (SYS32(S_CB_FLG) & 0x1u) why |= 1u << 9;                    /* door demo (not ported yet) */
    if (SYS32(S_LOOP_CT) != 1) why |= 1u << 10;
    if (*(volatile unsigned short *)(SYSP + S_SSV_MD0) != 0 || SYSF(S_SSV_AN) > 0.0f) why |= 1u << 12; /* screensaver */
    if (cvx_D.off) why |= 1u << 31;
    cvx_D.why_last = why;
    cvx_D.why_or |= why;
    return why;
}

/* ---- hook: bhMainSequence, between logic and draw (replaces jal bhControlLight) ---- */
void cvx_after_logic(void)
{
    int cur, prv, i;
    f32 *cm;
    state_check();
    bhControlLight();
    S.tick++;
    S.interp = interp_block() == 0;
    cur = S.tick & 1; prv = cur ^ 1;
    S.nent[cur] = 0;
    S.used[cur] = 0;
    cm = CAM_MTX;
    copy16(S.camraw[cur], cm);
    to_gx(S.cam[cur], cm);
    S.cam_tick[cur] = S.tick;
    S.cam_cut[cur] = CAM_NCUT;
    S.pers[cur] = CAM_PERS;
    S.gm_draw = SYSP ? SYS32(S_GM_FLG) : 0;
    for (i = 0; i < 3; i++) {
        S.campos[i] = *(volatile f32 *)(CAM_BASE + 0x0C + 4 * i);
        S.camang[i] = *(volatile int *)(CAM_BASE + 0x54 + 4 * i);
    }
    S.cam_ok = 0;
    if (S.cam_tick[prv] == S.tick - 1) {
        const f32 *a = S.cam[prv], *b = S.cam[cur];
        f32 dx = a[3] - b[3], dy = a[7] - b[7], dz = a[11] - b[11];
        f32 dt2 = dx * dx + dy * dy + dz * dz;
        f32 dt = dt2 > 0.0f ? dt2 * rsqrt(dt2) : 0.0f, dr = 0.0f, d, lim_t, lim_r;
        int zone, cut;
        for (i = 0; i < 12; i++) {
            if (i == 3 || i == 7 || i == 11) continue;
            d = fabsf_(a[i] - b[i]);
            if (d > dr) dr = d;
        }
        lim_t = 3.0f * S.cam_dt; lim_r = 3.0f * S.cam_dr;
        if (lim_t < 6.0f) lim_t = 6.0f;
        if (lim_r < 0.3f) lim_r = 0.3f;
        zone = S.cam_cut[prv] != S.cam_cut[cur];
        cut = dt > lim_t || dr > lim_r || dr > 0.9f || (zone && (dt > 1.5f || dr > 0.12f));
        if (S.interp) {
            if (cut) { if (zone) cvx_D.camcut++; else cvx_D.camfar++; }
            else { S.cam_ok = 1; cvx_D.camok++; }
        }
        S.cam_dt = dt;
        S.cam_dr = dr;
        S.nomodel = in_event() && (cut || S.cut_prev);
        S.cut_prev = cut;
    } else {
        S.cam_dt = S.cam_dr = 0.0f;
        S.nomodel = in_event();
        S.cut_prev = 1;
    }
}

/* ---- effects: per-kind lists on sys, drawn from px/py/pz (+0x10) and ax/ay/az (+0x1C); bhControlEffect
 * keeps last tick's values at +0x40..+0x54 (PS2 SYS_WORK offsets) ---- */
static const u32 EF_LISTS[][3] = {
    {0x222B8, 0x222E8, 512},   /* ef_pol: polygon models (shell casings) */
    {0x222BC, 0x22AE8, 128},   /* ef_mdf: shadows */
    {0x222C4, 0x234E8, 512},   /* ef_ntx */
    {0x222C8, 0x23CE8, 512},   /* ef_trs */
    {0x222CC, 0x244E8, 512},   /* ef_pnc */
    {0x222D0, 0x24CE8, 512},   /* ef_opq */
    {0x222D4, 0x254E8, 512},   /* ef_thl */
};
static struct { u8 *op; f32 p[3]; int a[3]; } ef_save[EF_SAVE_MAX];
static int ef_n;

/* Particle clouds (P_WRK via op->exp0 +0x2F0: num +0x10, pos[48] +0x1C) drawn from the ef_fnc list (count
 * sys+0x222E4, list sys+0x262E8) by bhEff_E00_DrawParticleSpr/Ply, e.g. the moths' poison spray. Each tick
 * moves every particle by its velocity plus a random jitter, so the previous positions can't be derived:
 * keep last tick's positions per cloud, draw frame A at the midpoint, restore the exact values after. */
#define A_DrawParticleSpr RG(0x0023DBB0u, 0x0023E200u, 0x0023D300u)
#define A_DrawParticlePly RG(0x0023DCB0u, 0x0023E300u, 0x0023D400u)
#define PTCL_SLOTS 32
typedef struct { u8 *pp; u32 tick; int num, used; f32 p[48][3]; } Ptcl;
static Ptcl ptcl[PTCL_SLOTS];

static void ptcl_mid(void)
{
    int n, i, k, j, num, cont;
    u8 **list, *op, *pp;
    u32 fn;
    Ptcl *sl, *fr;
    f32 *pos, *c, *o, c0, c1, c2, dx, dy, dz;
    n = (int)SYS32(0x222E4);
    if (n > 512) n = 512;
    list = (u8 **)(SYSP + 0x262E8);
    for (i = 0; i < n; i++) {
        op = list[i];
        if (!op) continue;
        fn = *(u32 *)(op + 0x4D4);
        if (fn != A_DrawParticleSpr && fn != A_DrawParticlePly) continue;
        pp = *(u8 **)(op + 0x2F0);
        if (!pp) continue;
        num = *(int *)(pp + 0x10);
        if (num <= 0 || num > 48) continue;
        sl = 0; fr = 0;
        for (k = 0; k < PTCL_SLOTS; k++) {
            if (ptcl[k].pp == pp) { sl = &ptcl[k]; break; }
            if (!fr && (!ptcl[k].pp || S.tick - ptcl[k].tick > 1)) fr = &ptcl[k];
        }
        cont = sl && sl->tick == S.tick - 1 && sl->num == num;
        if (!sl) sl = fr;
        if (!sl || sl->used) continue;
        pos = (f32 *)(pp + 0x1C);
        for (j = 0; j < num; j++) {
            c = pos + j * 3; o = sl->p[j];
            c0 = c[0]; c1 = c[1]; c2 = c[2];
            if (cont) {
                dx = c0 - o[0]; dy = c1 - o[1]; dz = c2 - o[2];
                if (dx * dx + dy * dy + dz * dz < 3.0f * 3.0f) {
                    c[0] = 0.5f * (o[0] + c0); c[1] = 0.5f * (o[1] + c1); c[2] = 0.5f * (o[2] + c2);
                }
            }
            o[0] = c0; o[1] = c1; o[2] = c2;
        }
        sl->pp = pp; sl->num = num; sl->tick = S.tick; sl->used = 1;
        cvx_D.ptcl++;
    }
}

static void ptcl_restore(void)
{
    int k, j;
    f32 *pos;
    for (k = 0; k < PTCL_SLOTS; k++) {
        if (!ptcl[k].used) continue;
        ptcl[k].used = 0;
        pos = (f32 *)(ptcl[k].pp + 0x1C);
        for (j = 0; j < ptcl[k].num; j++) {
            pos[j * 3] = ptcl[k].p[j][0]; pos[j * 3 + 1] = ptcl[k].p[j][1]; pos[j * 3 + 2] = ptcl[k].p[j][2];
        }
    }
}

/* Blood spray (bhEff302 -> E02_WORK via op->exp0, drawn from ef_fnc by bhEff_PtclSpriteDrawB): up to 6 stages
 * of 16 points. Each tick point k (counted from stage stg_stt) moves by dir[(vtx_num-1-k) & 15] * spd + the stage's
 * gravity (already updated), then spd += accel; the stage scale grows by scl_add_1st/2nd. All deterministic, so
 * frame A shifts each point half a step back in place and the scale half an add; the exact values are saved
 * and copied back after the draw. (The GameCube version restores by adding the step back where (p-h)+h == p;
 * the EE FPU truncates, so that check almost never holds here - a saved copy is exact on any FPU.) A stage
 * spawned this tick (stg_tim == 1) stays exact.
 * PS2 E02_WORK (types: 0xC0-byte attr backup): stt 4, num 8, vtx_num 0xC, accel 0x1C, erase 0x20, stg_tim 0x12C,
 * stg_buf 0x144, stg_grv 0x15C, vtx_dir 0x1A4, stg_spd 0x264, stg_scl 0x42C, scl_add 0x444/0x448. */
#define A_PtclSpriteDrawB RG(0x00248DB0u, 0x00249400u, 0x00248500u)
#define BLOOD_MAX 8
static u8 *bl_e[BLOOD_MAX];
static f32 bl_pos[BLOOD_MAX][96][3];
static f32 bl_scl[BLOOD_MAX][6];
static int bl_n, blood_on;

static void blood_walk(int restore)
{
    int i, n, b, stt, num, vn, erase, k, st, tim, fresh, tb, j, bit;
    u8 **list, *op, *e;
    f32 accel, *pos, *scl, su, h0, h1, h2, *sv;
    const f32 *dir, *grv, *spd, *d;
    if (!restore) {
        bl_n = 0;
        n = (int)SYS32(0x222E4);
        if (n > 512) n = 512;
        list = (u8 **)(SYSP + 0x262E8);
        for (i = 0; i < n && bl_n < BLOOD_MAX; i++) {
            op = list[i];
            if (!op || *(u32 *)(op + 0x4D4) != A_PtclSpriteDrawB) continue;
            e = *(u8 **)(op + 0x2F0);
            if (e) bl_e[bl_n++] = e;
        }
    }
    for (b = 0; b < bl_n; b++) {
        e = bl_e[b];
        stt = *(int *)(e + 4); num = *(int *)(e + 8); vn = *(int *)(e + 0xC); erase = *(int *)(e + 0x20);
        if (stt < 0 || num <= 0 || stt + num > 6 || vn != num * 16) continue;
        accel = *(f32 *)(e + 0x1C);
        dir = (const f32 *)(e + 0x1A4);
        k = 0;
        for (st = stt; st < stt + num; st++) {
            tim = *(int *)(e + 0x12C + st * 4);
            grv = (const f32 *)(e + 0x15C + st * 12);
            pos = *(f32 **)(e + 0x144 + st * 4);
            spd = *(f32 **)(e + 0x264 + st * 4);
            scl = (f32 *)(e + 0x42C + st * 4);
            fresh = tim <= 1;
            if (restore) *scl = bl_scl[b][st];
            else {
                bl_scl[b][st] = *scl;
                tb = tim - 1;
                if (!fresh && tb < erase) *scl -= 0.5f * *(f32 *)(e + ((tb < erase / 2) ? 0x444 : 0x448));
            }
            for (j = 0; j < 16; j++, k++, pos += 3) {
                bit = st * 16 + j;
                sv = bl_pos[b][bit];
                if (restore) { pos[0] = sv[0]; pos[1] = sv[1]; pos[2] = sv[2]; continue; }
                sv[0] = pos[0]; sv[1] = pos[1]; sv[2] = pos[2];
                if (fresh) continue;
                d = dir + ((vn - 1 - k) & 15) * 3;
                su = spd[j] - accel;
                h0 = 0.5f * (d[0] * su + grv[0]); h1 = 0.5f * (d[1] * su + grv[1]); h2 = 0.5f * (d[2] * su + grv[2]);
                pos[0] -= h0; pos[1] -= h1; pos[2] -= h2;
            }
        }
        if (!restore) cvx_D.blood++;
    }
}

/* Snow (bhEff219 -> EFF5SNOWRECT via op->exp0, drawn from ef_fnc by DrawEff5SnowRect): ExecEff5SnowRect moves
 * every flake each tick by wind + (0,-0.33,0) + its drift entry pSnowVector[i % 100] (per group), then wraps it into
 * a box around the camera. Frame A draws each flake half a step back; the exact positions are saved and copied
 * back (EE FPU: no exact add/subtract round trip). SnowGrp[20] at +0x3C (point ptr, count), pSnowVector +0xE0,
 * lSnowExistCrnt +0xE8. */
#define A_DrawEff5SnowRect RG(0x0025CEF0u, 0x0025D540u, 0x0025C640u)
#define GetSnowWind FN(RG(0x0025D4E0, 0x0025DB30, 0x0025CC30), f32 *, void *, f32 *)
#define SNOW_MAX 2048
static f32 snow_save[SNOW_MAX][3];
static int snow_on;

static void snow_walk(int restore)
{
    int n, i, g, m, rest, k, bit = 0;
    u8 **list, *op, *sn;
    f32 w[3], *vec, *pt, *sv;
    n = (int)SYS32(0x222E4);
    if (n > 512) n = 512;
    list = (u8 **)(SYSP + 0x262E8);
    for (i = 0; i < n; i++) {
        op = list[i];
        if (!op || *(u32 *)(op + 0x4D4) != A_DrawEff5SnowRect) continue;
        sn = *(u8 **)(op + 0x2F0);
        if (!sn) continue;
        if (!restore) { GetSnowWind(sn, w); w[1] -= 0.33f; cvx_D.snow++; }
        vec = *(f32 **)(sn + 0xE0);
        rest = *(int *)(sn + 0xE8);
        for (g = 0; g < 20 && rest > 0; g++) {
            pt = *(f32 **)(sn + 0x3C + g * 8);
            m = *(int *)(sn + 0x40 + g * 8);
            if (m > rest) m = rest;
            rest -= m;
            for (k = 0; k < m && bit < SNOW_MAX; k++, bit++, pt += 3) {
                sv = snow_save[bit];
                if (restore) { pt[0] = sv[0]; pt[1] = sv[1]; pt[2] = sv[2]; continue; }
                sv[0] = pt[0]; sv[1] = pt[1]; sv[2] = pt[2];
                pt[0] -= 0.5f * (w[0] + vec[k * 3]);
                pt[1] -= 0.5f * (w[1] + vec[k * 3 + 1]);
                pt[2] -= 0.5f * (w[2] + vec[k * 3 + 2]);
            }
        }
    }
}

static void eff_mid(void)
{
    u32 l;
    int n, i, k, da;
    u8 **list, *op;
    f32 *cur, *old, dx, dy, dz;
    int *ang, *ang_old;
    ef_n = 0;
    if (S.nomodel) return;
    for (l = 0; l < sizeof(EF_LISTS) / sizeof(EF_LISTS[0]); l++) {
        n = (int)SYS32(EF_LISTS[l][0]);
        if (n > (int)EF_LISTS[l][2]) n = (int)EF_LISTS[l][2];
        list = (u8 **)(SYSP + EF_LISTS[l][1]);
        for (i = 0; i < n && ef_n < EF_SAVE_MAX; i++) {
            op = list[i];
            if (!op) continue;
            cur = (f32 *)(op + 0x10); old = (f32 *)(op + 0x40);
            ang = (int *)(op + 0x1C); ang_old = (int *)(op + 0x4C);
            dx = cur[0] - old[0]; dy = cur[1] - old[1]; dz = cur[2] - old[2];
            if (dx * dx + dy * dy + dz * dz > 3.0f * 3.0f) continue;   /* spawned/teleported: exact */
            ef_save[ef_n].op = op;
            for (k = 0; k < 3; k++) { ef_save[ef_n].p[k] = cur[k]; ef_save[ef_n].a[k] = ang[k]; }
            ef_n++;
            for (k = 0; k < 3; k++) {
                cur[k] = 0.5f * (cur[k] + old[k]);
                da = (short)((ang[k] - ang_old[k]) & 0xFFFF);
                ang[k] = ang_old[k] + da / 2;
            }
        }
    }
    ptcl_mid();
    blood_walk(0);
    blood_on = 1;
    snow_walk(0);
    snow_on = 1;
}

static void eff_restore(void)
{
    int k;
    u8 *op;
    if (snow_on) { snow_walk(1); snow_on = 0; }
    ptcl_restore();
    if (blood_on) { blood_walk(1); blood_on = 0; }
    while (ef_n > 0) {
        ef_n--;
        op = ef_save[ef_n].op;
        for (k = 0; k < 3; k++) {
            ((f32 *)(op + 0x10))[k] = ef_save[ef_n].p[k];
            ((int *)(op + 0x1C))[k] = ef_save[ef_n].a[k];
        }
    }
}

/* ---- bones: ML_WORK owP array, O_WORK stride 0x50, 4x4 world matrix at +0x10 ---- */
#define BONE(ow, i) ((f32 *)((ow) + (i) * 0x50 + 0x10))

static void bones_restore(void)
{
    int cur = S.tick & 1, i, b;
    Ent *e;
    for (i = 0; i < S.nent[cur]; i++) {
        e = &S.ent[cur][i];
        if (!e->prev) continue;
        for (b = 0; b < e->n; b++) from_gx(BONE(e->key, b), e->cur + b * 12);
    }
}

/* ---- hook: the draw-all call in bhMainSequence (frame A) ---- */
void cvx_alldraw(void)
{
    int cur, fov;
    f32 *cm, mid[12];
    state_check();
    if (!S.interp || S.phase || !S.cam_ok) {
        if (S.interp && !S.phase) { eff_mid(); S.in_a = 1; }
        bhAllDrawModel();
        S.in_a = 0;
        eff_restore();
        if (S.interp && !S.phase) bones_restore();
        return;
    }
    cur = S.tick & 1;
    cm = CAM_MTX;
    cam_mid_s(mid, S.cam[cur ^ 1], S.cam[cur]);
    from_gx(cm, mid);
    fov = S.pers[cur ^ 1] != S.pers[cur];
    if (fov) njSetPerspective((S.pers[cur ^ 1] + S.pers[cur]) / 2);
    bhSetLight();   /* lights live in view space: re-apply for the in-between camera */
    eff_mid();
    S.in_a = 1;
    bhAllDrawModel();
    S.in_a = 0;
    eff_restore();
    bones_restore();
    copy16(cm, S.camraw[cur]);
    if (fov) njSetPerspective(S.pers[cur]);
}

/* ---- hook: bhPutModel entry ---- */
extern void PutModelOrig(u8 *ewP);

static Ent *lookup(int pool, u8 *key, int n)
{
    int i;
    for (i = 0; i < S.nent[pool]; i++)
        if (S.ent[pool][i].key == key && S.ent[pool][i].n == n) return &S.ent[pool][i];
    return 0;
}

void cvx_putmodel(u8 *ewP)
{
    u32 *ml;
    int n, cur, i;
    u8 *ow;
    Ent *e, *p;
    f32 tmp[12];
    state_check();
    if (!S.interp && !S.phase) { PutModelOrig(ewP); return; }
    ml = *(u32 **)(ewP + 0x2E0);
    n = ml ? (int)ml[1] : 0;
    ow = ml ? (u8 *)ml[5] : 0;
    if (!ow || n <= 0 || n > 64) { PutModelOrig(ewP); return; }
    cur = S.tick & 1;
    e = lookup(cur, ow, n);
    if (S.phase) {
        /* exact frame: the bones as they were at this tick's draw */
        if (!e) { PutModelOrig(ewP); return; }
        for (i = 0; i < n; i++) {
            copy16(S.scratch + i * 16, BONE(ow, i));
            from_gx(BONE(ow, i), e->cur + i * 12);
        }
        PutModelOrig(ewP);
        for (i = 0; i < n; i++) copy16(BONE(ow, i), S.scratch + i * 16);
        return;
    }
    if (!e) {
        if (S.nent[cur] >= MAXENT || S.used[cur] + n > POOLMTX ||
            (ewP != PLP && S.used[cur] + n > POOLMTX - PLAYER_RESERVE)) { PutModelOrig(ewP); return; }
        e = &S.ent[cur][S.nent[cur]++];
        e->key = ow;
        e->n = n;
        e->cur = &S.pool[cur][S.used[cur] * 12];
        S.used[cur] += n;
        for (i = 0; i < n; i++) to_gx(e->cur + i * 12, BONE(ow, i));
        p = lookup(cur ^ 1, ow, n);
        e->prev = 0;
        if (p && !S.nomodel && S.cam_tick[cur ^ 1] == S.tick - 1 &&
            (in_event() ? pose_close(p->cur, e->cur, n, 3.0f) : mtx_close(p->cur, e->cur, 3.0f))) e->prev = p->cur;
        else if (p && !S.nomodel && S.cam_tick[cur ^ 1] == S.tick - 1) cvx_D.poserej++;
    }
    if (!e->prev) { PutModelOrig(ewP); return; }
    for (i = 0; i < n; i++) {
        mtx_mid(tmp, e->prev + i * 12, e->cur + i * 12);
        from_gx(BONE(ow, i), tmp);
    }
    PutModelOrig(ewP);
    /* inside frame A the pose stays in-between until bones_restore() (attached effects follow it) */
    if (!S.in_a)
        for (i = 0; i < n; i++) from_gx(BONE(ow, i), e->cur + i * 12);
}

/* Message/subtitle window: bhControlMessage steps the text and draws it in one go (called from the game task
 * while st_flg 0x200, mode = ts_flg 0x200 ? 0 : 1). Redraw it for the extra frame with everything it touches
 * saved and restored - flag words 0x54-0x7C, pads 0x1B0B0-0x1B0CC (zeroed during the call, so nothing can
 * advance or beep), message state 0x289B4-0x28A50 - as on the GameCube. */
#define bhControlMessage FN(RG(0x002B7670, 0x002BD150, 0x002B6C60), void, int)
static u32 msg_flags[11], msg_pad[8], msg_mes[39];
static void draw_message(void)
{
    int i;
    if (!(SYS32(S_ST_FLG) & 0x200u)) return;
    for (i = 0; i < 11; i++) msg_flags[i] = SYS32(0x54 + 4 * i);
    for (i = 0; i < 8; i++) { msg_pad[i] = SYS32(0x1B0B0 + 4 * i); SYS32(0x1B0B0 + 4 * i) = 0; }
    for (i = 0; i < 39; i++) msg_mes[i] = SYS32(0x289B4 + 4 * i);
    bhControlMessage((SYS32(S_TS_FLG) & 0x200u) ? 0 : 1);
    for (i = 0; i < 11; i++) SYS32(0x54 + 4 * i) = msg_flags[i];
    for (i = 0; i < 8; i++) SYS32(0x1B0B0 + 4 * i) = msg_pad[i];
    for (i = 0; i < 39; i++) SYS32(0x289B4 + 4 * i) = msg_mes[i];
}

/* ---- the exact extra frame ---- */
static void draw_only(void)
{
    f32 *cm = CAM_MTX, live[16];
    int pers_live = CAM_PERS, cur = S.tick & 1;
    u8 sleep = PL_SLEEP;
    copy16(live, cm);
    copy16(cm, S.camraw[cur]);
    njSetPerspective(S.pers[cur]);
    bhSetLight();   /* the tick's draw ended in character half-light */
    bhAllDrawModel();
    copy16(cm, live);
    njSetPerspective(pers_live);
    PL_SLEEP = sleep;
    draw_message();
    if (SYSF(S_CINE_AN) > 0.0f) bhDrawCinesco();
    /* sniper scope overlay (tint, reticle, zoom readout from cam.pers): pure 2D, this tick's zoom */
    if (SYS32(S_ST_FLG) & 0x800000u) {
        CAM_PERS = S.pers[cur];
        bhDrawScope();
        CAM_PERS = pers_live;
    }
    if (SYSF(S_FADE_AN) > 0.0f) bhDrawScreenFade();
    /* self-destruct countdown and Battle Game timer: the draw half of bhSysCallScreenSaver's timer blocks (its
     * voice callouts stay in the tick); bhDispTime only reads and draws */
    {
        f32 pos[2];
        int t = (int)SYS32(S_EVT_TIM);
        if (t != 0 && (SYS32(0x70) & 0x200u) && (SYS32(S_SS_FLG) & 0x40u) && !bhCkFlg(SYSP + 0x190, 349)) {
            pos[0] = 222.0f; pos[1] = 76.0f;
            bhDispTime(pos, 7, t, t < (int)SYS32(0x1B168) ? 2 : 3, -0.9f);
        }
        if (SYS32(S_GM_MODE) == 3 && (SYS32(0x70) & 0x200u) && !(SYS32(S_TS_FLG) & 0x80u) && (SYS32(S_GM_FLG) & 0x80000000u)) {
            pos[0] = 222.0f; pos[1] = 76.0f;
            bhDispTime(pos, 7, (int)SYS32(0x8A0), 3, -0.9f);
        }
    }
}

/* ---- door transitions ----
 * bhSysCallDoordemo (task 11) calls bhControlDoor once per tick (jal at 0x133D4C): logic procs (camera path, door
 * leaf, lights, fade), one-shot sound triggers, then a self-contained draw of the door scene from DoorWrk's view
 * position/angles and the door model. With status bit 0x80 the procs are skipped but the draw still runs, so the
 * scene can be redrawn with an in-between view and door pose. Same scheme as the GameCube mod. DoorWrk 0x4F78A0:
 * status +0x08, vew_pos +0x58, vew_ang +0x70, objP +0xD0; CNK object: pos +0x08, ang +0x14, child +0x2C,
 * sibling +0x30. (PCSX2's built-in "Door Transition Skip" patch removes the bhControlDoor call: nothing to do then.) */
#define DOORWRK RG(0x004F78A0, 0x0050F4C0, 0x005053E0)
#define DOOR_STATUS (*(volatile u32 *)(DOORWRK + 0x08))
#define DOOR_VPOS ((volatile f32 *)(DOORWRK + 0x58))
#define DOOR_VANG ((volatile int *)(DOORWRK + 0x70))
#define DOOR_OBJP (*(u8 **)(DOORWRK + 0xD0))
#define bhControlDoor FN(RG(0x002AF370, 0x002B4DE0, 0x002AE8F0), int, void)
#define DOOR_MAXN 32
static struct {
    u32 n;
    int pending;
    u32 slot_n[2];
    u8 *objp[2];
    int nn[2];
    u8 *node[2][DOOR_MAXN];
    f32 vpos[2][3];
    int vang[2][3];
    f32 npos[2][DOOR_MAXN][3];
    int nang[2][DOOR_MAXN][3];
} DR;

static int door_nodes(u8 *root, u8 **out)
{
    u8 *stack[DOOR_MAXN], *o, *sib, *child;
    int sp = 0, n = 0;
    if (root) stack[sp++] = root;
    while (sp && n < DOOR_MAXN) {
        o = stack[--sp];
        out[n++] = o;
        sib = *(u8 **)(o + 0x30); child = *(u8 **)(o + 0x2C);
        if (sib && sp < DOOR_MAXN) stack[sp++] = sib;
        if (child && sp < DOOR_MAXN) stack[sp++] = child;
    }
    return n;
}

static void door_snapshot(void)
{
    u32 st = DOOR_STATUS;
    int k, i, j;
    if (!(st & 0x200) || (st & 0x40) || !DOOR_OBJP) return;
    k = ++DR.n & 1;
    DR.slot_n[k] = DR.n;
    DR.objp[k] = DOOR_OBJP;
    DR.nn[k] = door_nodes(DOOR_OBJP, DR.node[k]);
    for (j = 0; j < 3; j++) { DR.vpos[k][j] = DOOR_VPOS[j]; DR.vang[k][j] = DOOR_VANG[j]; }
    for (i = 0; i < DR.nn[k]; i++)
        for (j = 0; j < 3; j++) {
            DR.npos[k][i][j] = ((f32 *)(DR.node[k][i] + 0x08))[j];
            DR.nang[k][i][j] = ((int *)(DR.node[k][i] + 0x14))[j];
        }
    DR.pending = 1;
}

/* replaces jal bhControlDoor in bhSysCallDoordemo */
int cvx_controldoor(void)
{
    int r;
    state_check();
    r = bhControlDoor();
    door_snapshot();
    return r;
}

static int amid(int a, int b) { return a + (short)((b - a) & 0xFFFF) / 2; }

/* put slot k's values back (or the midpoint between slots p and k) into the live door work */
static void door_apply(int k, int p, int mid)
{
    int i, j;
    for (j = 0; j < 3; j++) {
        DOOR_VPOS[j] = mid ? 0.5f * (DR.vpos[p][j] + DR.vpos[k][j]) : DR.vpos[k][j];
        DOOR_VANG[j] = mid ? amid(DR.vang[p][j], DR.vang[k][j]) : DR.vang[k][j];
    }
    for (i = 0; i < DR.nn[k]; i++)
        for (j = 0; j < 3; j++) {
            ((f32 *)(DR.node[k][i] + 0x08))[j] = mid ? 0.5f * (DR.npos[p][i][j] + DR.npos[k][i][j]) : DR.npos[k][i][j];
            ((int *)(DR.node[k][i] + 0x14))[j] = mid ? amid(DR.nang[p][i][j], DR.nang[k][i][j]) : DR.nang[k][i][j];
        }
}

static void door_redraw(void)
{
    u32 st = DOOR_STATUS;
    DOOR_STATUS = st | 0x80;   /* procs paused: draw only */
    bhControlDoor();
    DOOR_STATUS = st;
}

/* Ps2SwapDBuff with a one-vblank wait */
static void swap(int tick_frame)
{
    SyncPath();
    Ps2DrawOTag();
    Ps2ClearOT();
    SyncPath();
    if (tick_frame) EorFunc();
    while (Ps2_vcount < 1) { __asm__ volatile("nop"); }
    PS2_swap();
    sceGsSwapDBuffDc(Db, Ps2_dbuff);
    Ps2_dbuff = (Ps2_dbuff + 1) & 1;
    Ps2_vcount = 0;
    T0_COUNT = 0;
    if (tick_frame) VsyncFunc();
    cvx_D.frames++;
}

/* A cut applied after this tick's draw (requested via gm_flg 0x1000/0x2000, or applied on the spot by
 * bhCheckCut -> bhSetCut, which sets gm_flg 0x20 and hides the new shot's room parts) would make the exact
 * frame draw the old view with the new shot's hidden geometry (missing walls / a lone wall). Zone handovers
 * of the follow camera also go through bhSetCut but keep the camera continuous, so only count a cut when
 * the camera was really relocated. Same rule as the GameCube mod. */
static int cut_after_draw(void)
{
    int k, da, relocated = 0;
    f32 d, d2 = 0.0f;
    int cut = (S.gm_draw & 0x3000) || ((SYS32(S_GM_FLG) & 0x20) && !(S.gm_draw & 0x20)) ||
              CAM_NCUT != S.cam_cut[S.tick & 1];
    if (!cut) return 0;
    for (k = 0; k < 3; k++) {
        d = *(volatile f32 *)(CAM_BASE + 0x0C + 4 * k) - S.campos[k];
        d2 += d * d;
        da = (*(volatile int *)(CAM_BASE + 0x54 + 4 * k) - S.camang[k]) & 0xFFFF;
        if (da > 0x8000) da = 0x10000 - da;
        if (da > 0x800) relocated = 1;      /* > ~11 degrees in one tick */
    }
    if (d2 > 6.0f * 6.0f) relocated = 1;
    return relocated;
}

/* ---- hook: njUserMain, replaces jal PS2_jikken (pad read + Ps2SwapDBuff) ---- */
/* A door tick: the door task already drew the exact scene into the OT. Replace it with the in-between scene for
 * frame A (one vblank), then draw the exact scene as frame B. */
static int door_frame(void)
{
    int k = DR.n & 1, p = k ^ 1, mid, j, da;
    u32 st;
    f32 dx, dy, dz;
    if (cvx_D.off || Ps2_vcount >= 1) { cvx_D.door_bail[0]++; return 0; }
    if (DR.slot_n[p] != DR.n - 1 || DR.objp[p] != DR.objp[k] || DR.nn[p] != DR.nn[k]) { cvx_D.door_bail[1]++; return 0; }
    st = DOOR_STATUS;
    if (!(st & 0x200) || (st & 0x40) || DOOR_OBJP != DR.objp[k]) { cvx_D.door_bail[2]++; return 0; }
    /* a jump inside the door sequence: show it exact in both frames */
    dx = DR.vpos[k][0] - DR.vpos[p][0]; dy = DR.vpos[k][1] - DR.vpos[p][1]; dz = DR.vpos[k][2] - DR.vpos[p][2];
    mid = dx * dx + dy * dy + dz * dz < 20.0f * 20.0f;
    for (j = 0; j < 3; j++) {
        da = (DR.vang[k][j] - DR.vang[p][j]) & 0xFFFF;
        if (da > 0x8000) da = 0x10000 - da;
        if (da > 0x2000) mid = 0;
    }
    pdGetPeripheral(0);
    if (mid) {
        Ps2ClearOT();              /* drop the exact scene the tick drew */
        door_apply(k, p, 1);
        door_redraw();
        door_apply(k, p, 0);
    }
    swap(1);                       /* frame A */
    st = DOOR_STATUS;
    if ((st & 0x200) && !(st & 0x40)) {
        S.phase = 1;
        door_redraw();             /* frame B: exact */
        swap(0);
        S.phase = 0;
        cvx_D.door++;
    } else {
        while (Ps2_vcount < 1) { __asm__ volatile("nop"); }
    }
    return 1;
}

void cvx_frame(void)
{
    state_check();
    if (DR.pending) {
        DR.pending = 0;
        if (!S.interp && door_frame()) return;
    }
    if (!S.interp) { cvx_D.vanilla++; PS2_jikken(); return; }
    S.interp = 0;
    if (cut_after_draw()) {          /* this tick's frame A is shown for the full tick, as without the mod */
        cvx_D.bskip++;
        PS2_jikken();
        return;
    }
    pdGetPeripheral(0);
    if (Ps2_vcount >= 1) {           /* the tick ran long: present A now, no extra frame */
        cvx_D.late++;
        swap(1);
        return;
    }
    swap(1);                         /* frame A: this tick's (in-between) draw */
    S.phase = 1;
    draw_only();                     /* frame B: exact */
    swap(0);
    S.phase = 0;
    cvx_D.extra++;
}

#ifdef CVX_LAB
/* ---- lab: test input. Task table slot 6 (bhSysCallPad) -> cvx_syscallpad: after the pad read, OR test buttons
 * into sys->pad_on / pad_ps. (Slot 6 always runs; the game task is suspended while e.g. a message is up.) ---- */
#define bhSysCallPad FN(RG(0x00132B70, 0x00132DF0, 0x00132A70), void, void)
void cvx_syscallgame(void)
{
    state_check();
    bhSysCallPad();
    if (cvx_D.fake_on && SYSP) SYS32(0x1B0B0) |= cvx_D.fake_on;
    if (cvx_D.fake_ps && SYSP) { SYS32(0x1B0B8) |= cvx_D.fake_ps; cvx_D.fake_ps = 0; }
}
#endif

/* ---- entry wrappers: the game's code keeps 128-bit values in s0-s7/fp (MWCC saves them with sq);
 * ee-gcc only saves 64 bits, so every hook enters through a wrapper that saves the full registers ---- */
/* .set noreorder: otherwise the assembler moves the stack restore out of jr's delay slot */
#define WRAP(name, fn) \
__asm__(".text\n .set noreorder\n .globl " #name "\n .ent " #name "\n" #name ":\n" \
        " addiu $29, $29, -0xA0\n sq $16, 0x00($29)\n sq $17, 0x10($29)\n sq $18, 0x20($29)\n sq $19, 0x30($29)\n" \
        " sq $20, 0x40($29)\n sq $21, 0x50($29)\n sq $22, 0x60($29)\n sq $23, 0x70($29)\n sq $30, 0x80($29)\n" \
        " sq $31, 0x90($29)\n jal " #fn "\n nop\n" \
        " lq $16, 0x00($29)\n lq $17, 0x10($29)\n lq $18, 0x20($29)\n lq $19, 0x30($29)\n lq $20, 0x40($29)\n" \
        " lq $21, 0x50($29)\n lq $22, 0x60($29)\n lq $23, 0x70($29)\n lq $30, 0x80($29)\n lq $31, 0x90($29)\n" \
        " jr $31\n addiu $29, $29, 0xA0\n .end " #name "\n .set reorder\n");
WRAP(w_frame, cvx_frame)
WRAP(w_after_logic, cvx_after_logic)
WRAP(w_alldraw, cvx_alldraw)
WRAP(w_putmodel, cvx_putmodel)
WRAP(w_controldoor, cvx_controldoor)
#ifdef CVX_LAB
WRAP(w_syscallgame, cvx_syscallgame)
#endif

/* bhPutModel's first two instructions, relocated (the hook overwrites them with j w_putmodel + nop) */
__asm__(".text\n .set noreorder\n .globl PutModelOrig\n .ent PutModelOrig\nPutModelOrig:\n"
        " .word 0x27BDFFA0\n"     /* addiu sp, sp, -0x60 */
        " .word 0x7FBF0050\n"     /* sq ra, 0x50(sp) */
#ifdef CVX_PAL
        " .word 0x0804BACE\n"     /* j 0x0012EB38 (rest of bhPutModel, PAL) */
#else
        " .word 0x0804BAEE\n"     /* j 0x0012EBB8 (rest of bhPutModel) */
#endif
        " nop\n .end PutModelOrig\n .set reorder\n");
