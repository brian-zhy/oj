/* no_opt_pragma.cc —— 禁止选手自行控制优化等级的 GCC 插件
 *
 * 作用：拦截 `#pragma GCC optimize ...`（含 push_options/pop_options）以及
 *       `__attribute__((optimize(...)))`，命中即报编译错误（CE），
 *       防止选手在评测中私自提升/降低优化等级获得不公平优势。
 *
 * 原理：上述两种写法最终都会变成函数 decl 上的 "optimize" 属性。
 *       本插件注册一个 GIMPLE pass，在每个函数上检查该属性。
 *       因为检查发生在预处理之后，所以 _Pragma("GCC optimize(...)")、
 *       宏拼接等绕过手段同样会被捕获——这是纯文本扫描做不到的。
 *
 * 需要与评测所用 GCC 严格同版本的插件头文件（gcc-N-plugin-dev）。
 */

#include "gcc-plugin.h"
#include "plugin-version.h"
#include "context.h"
#include "tree.h"
#include "stringpool.h"   /* get_identifier* —— attribs.h 依赖它 */
#include "attribs.h"      /* lookup_attribute */
#include "function.h"
#include "tree-pass.h"
#include "gimple.h"
#include "diagnostic.h"   /* error_at */

/* 任何 GCC 插件都必须声明这一全局符号。 */
int plugin_is_GPL_compatible;

namespace {

const pass_data no_opt_pragma_pass_data = {
  GIMPLE_PASS,      /* type                */
  "no_opt_pragma",  /* name                */
  OPTGROUP_NONE,    /* optinfo_flags       */
  TV_NONE,          /* tv_id               */
  PROP_gimple_any,  /* properties_required */
  0,                /* properties_provided */
  0,                /* properties_destroyed*/
  0,                /* todo_flags_start    */
  0,                /* todo_flags_finish   */
};

class no_opt_pragma_pass : public gimple_opt_pass
{
public:
  no_opt_pragma_pass (gcc::context *ctxt)
    : gimple_opt_pass (no_opt_pragma_pass_data, ctxt)
  {}

  /* 每个函数都会调用一次。 */
  unsigned int execute (function *fun) final override
  {
    tree attrs = DECL_ATTRIBUTES (fun->decl);
    if (attrs && lookup_attribute ("optimize", attrs))
      error_at (DECL_SOURCE_LOCATION (fun->decl),
                "optimize attribute or pragma is not allowed");
    return 0;
  }
};

} // namespace

int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version)
{
  /* 插件与编译器版本不匹配时直接拒绝加载，避免产生难以理解的崩溃。 */
  if (!plugin_default_version_check (version, &gcc_version))
    return 1;

  register_pass_info pass_info;
  pass_info.pass = new no_opt_pragma_pass (g);
  /* 在第一个 SSA pass 之前运行：既早于所有优化，又保证函数体已 gimplify。 */
  pass_info.reference_pass_name = "ssa";
  pass_info.ref_pass_instance_number = 1;
  pass_info.pos_op = PASS_POS_INSERT_BEFORE;

  register_callback (plugin_info->base_name, PLUGIN_PASS_MANAGER_SETUP,
                     NULL, &pass_info);

  return 0;
}
