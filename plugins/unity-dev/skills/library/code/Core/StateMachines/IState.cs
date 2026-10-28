namespace Company.Product.Core.StateMachines
{
    public interface IState
    {
        void Enter();
        void Exit();
    }
}
