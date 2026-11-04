namespace ProjectName.Core.UI
{
    // A graphic that draws its own shape, such as an SDF rounded rectangle in a shader, tells the UI checks its corner size
    // in canvas units, since they can't measure it from a sprite.
    public interface IUiShape
    {
        float CornerRadius { get; }
    }
}
